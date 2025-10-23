"""
XRD Recipe Management Module
============================
Functions for loading and parsing recipe JSON files for XRD data processing.
Converts recipe dictionaries to GSASParams objects for processing.

This module consolidates recipe handling to avoid circular dependencies
between data_generator and gsas_processing modules.

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import json
import os
from typing import Dict

# Import data structures from core module
from XRD.core.gsas_processing import GSASParams, PeakParams, Stages


def load_recipe_from_file(recipe_path: str) -> dict:
    """
    Load recipe JSON from file.

    Args:
        recipe_path: Path to recipe JSON file

    Returns:
        dict: Recipe dictionary with all processing parameters
    """
    with open(recipe_path, 'r') as f:
        return json.load(f)


def create_gsas_params_from_recipe(recipe: dict) -> GSASParams:
    """
    Convert recipe dictionary to GSASParams object.

    This function handles all the conversions and validation needed to create
    a complete GSASParams object from a recipe JSON file. It handles:
    - Peak parameter conversion
    - Stage enum conversion
    - Path resolution
    - Detector parameter extraction
    - Backward compatibility with legacy recipe formats

    Args:
        recipe: Dictionary loaded from recipe JSON file

    Returns:
        GSASParams: Fully configured parameters object ready for processing

    Raises:
        ValueError: If required fields are missing or invalid
    """
    # Convert active peaks (required analysis peaks)
    active_peaks = [PeakParams.from_dict(peak) for peak in recipe['active_peaks']]

    # Convert available peaks (background/interference peaks)
    available_peaks = []
    if 'AVAILABLE_PEAKS' in recipe and recipe['AVAILABLE_PEAKS']:
        for i, peak_data in enumerate(recipe['AVAILABLE_PEAKS']):
            if isinstance(peak_data, dict):
                # Full metadata provided
                available_peaks.append(PeakParams.from_dict(peak_data))
            else:
                # Just a position - auto-generate metadata
                available_peaks.append(PeakParams(
                    name=f"Unknown {i+1}",
                    miller_index="000",
                    position=float(peak_data),
                    limits=(peak_data - 0.2, peak_data + 0.2)
                ))

    # Handle exposure in setting name if needed
    setting = recipe['setting']
    exposure = recipe.get('exposure', '019')
    if setting in ['SpeedTall', 'Speed'] and exposure != '1':
        setting = f"{setting}{exposure}"

    # Convert stage string to enum (handle case variations)
    stage_name = recipe['stage'].upper()
    if stage_name == 'BEF':
        stage = Stages.BEF
    elif stage_name == 'AFT':
        stage = Stages.AFT
    elif stage_name == 'CONT':
        stage = Stages.CONT
    elif stage_name == 'DELT':
        stage = Stages.DELT
    else:
        stage = Stages[stage_name]  # Fallback to direct enum lookup

    # Extract detector parameters (REQUIRED for calibration and d-spacing)
    detector_params = recipe.get('detector_params', {})
    pixel_size = tuple(detector_params.get('pixel_size', [172.0, 172.0]))
    wavelength = detector_params.get('wavelength', 0.240)
    detector_size = tuple(detector_params.get('detector_size', [1475, 1679]))

    # Get home directory (for outputs)
    home_dir = recipe.get('home_dir', os.getcwd())

    # Get explicit input paths
    # Try new format first, then fall back to old format for backward compatibility
    images_path = recipe.get('images_path')
    if not images_path:
        # Legacy fallback: try to construct from old image_folder
        if 'image_folder' in recipe:
            images_path = recipe['image_folder']
            print(f"Warning: Using legacy 'image_folder' field. Please update recipe to use 'images_path'.")
        else:
            raise ValueError("Recipe must specify 'images_path' for input images directory")

    # References are optional (None if not available)
    refs_path = recipe.get('refs_path', None)
    if refs_path == "":  # Empty string means no refs
        refs_path = None

    return GSASParams(
        home_dir=home_dir,
        images_path=images_path,
        refs_path=refs_path,
        control_file=recipe['control_file'],
        mask_file=recipe['mask_file'],
        intplot_export=recipe.get('intplot_export', False),
        sample=recipe['sample'],
        setting=setting,
        stage=stage,
        notes=recipe.get('notes', ''),
        exposure=exposure,
        active_peaks=active_peaks,
        available_peaks=available_peaks,
        azimuths=(recipe['az_start'], recipe['az_end']),
        frames=(recipe['frame_start'], recipe['frame_end']),
        spacing=recipe['spacing'],
        step=recipe['step'],
        pixel_size=pixel_size,
        wavelength=wavelength,
        detector_size=detector_size
    )
