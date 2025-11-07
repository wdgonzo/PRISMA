#!/usr/bin/env python3
"""
XRD Data Generation Module
==========================
Pure data processing pipeline extracted from the visualization system.
Focuses only on generating Zarr data files from diffraction images using GSAS-II.

This module is designed for:
- Headless operation on supercomputers
- Batch processing workflows
- Data generation without visualization overhead

Main Features:
- GSAS-II peak fitting with background peak interference filtering
- Unified 4D data structure storage in Zarr format
- Parallel processing with Dask
- No GUI or visualization dependencies

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import json
import os
import sys

# Import the unified processing module
from XRD.core.gsas_processing import (
    XRDDataset, GSASParams, Stages, PeakParams,
    load_or_process_data, subtract_datasets
)
from XRD.processing.recipes import create_gsas_params_from_recipe, load_recipe_from_file
from XRD.hpc.cluster import get_dask_client, close_dask_client


def generate_data_from_recipe(recipe: dict, recipe_name: str = None, client=None) -> XRDDataset:
    """
    Generate XRD data from recipe configuration.

    Args:
        recipe: Recipe dictionary from JSON file
        recipe_name: Optional recipe name for unique Zarr path generation
        client: Optional Dask client (for batch processing). If None, creates local client.

    Returns:
        XRDDataset object containing processed data
    """
    # Initialize Dask client for parallel processing - auto-detects HPC/local mode
    # Only create a new client if one wasn't provided (for standalone use)
    should_close_client = False
    if client is None:
        client = get_dask_client()
        should_close_client = True

    try:
        # Extract detector parameters (REQUIRED)
        detector_params = recipe.get('detector_params', {})
        pixel_size = tuple(detector_params.get('pixel_size', [172.0, 172.0]))
        wavelength = detector_params.get('wavelength', 0.240)
        detector_size = tuple(detector_params.get('detector_size', [1475, 1679]))

        print(f"\n{'='*60}")
        print(f"Detector Configuration:")
        print(f"   Pixel size: {pixel_size} μm")
        print(f"   Wavelength: {wavelength} Å")
        print(f"   Detector size: {detector_size} pixels")
        print(f"{'='*60}")

        # Handle calibration (auto or manual)
        calibration_config = recipe.get('calibration', {})
        if calibration_config.get('auto_calibrate', False):
            # Import calibration module only if needed
            from XRD.utils.calibration import get_or_create_calibration

            control_file = get_or_create_calibration(
                recipe,
                recipe['setting'],
                pixel_size,
                wavelength,
                detector_size
            )
            print(f"\nUsing auto-generated calibration: {os.path.basename(control_file)}")

            # Update recipe with the calibration file for GSASParams creation
            recipe['control_file'] = control_file
        else:
            control_file = recipe['control_file']
            print(f"\nUsing manual calibration: {os.path.basename(control_file)}")

        # Convert recipe to processing parameters
        params = create_gsas_params_from_recipe(recipe)
        ref_steps = recipe["refine_steps"] if "refine_steps" in recipe else [[{"area":False,"pos":False,"sig":False,"gam":False}, [False, True, False, False]]]

        print(f"\nProcessing recipe:")
        print(f"   Sample: {params.sample}")
        print(f"   Setting: {params.setting}")
        print(f"   Stage: {params.stage.name}")
        print(f"   Peaks: {[peak.name for peak in params.active_peaks]}")
        #print(f"   Image folder: {params.image_folder}")

        # Note: Peak metadata is now stored in params.active_peaks and params.available_peaks
        # Created by create_gsas_params_from_recipe() - no need to pass separately

        # Create required submitted_values.json for compatibility
        submitted_values = {
            "force_reprocess": True,
            "analyze option": "Accurate"
        }

        with open('submitted_values.json', 'w') as f:
            json.dump(submitted_values, f, indent=2)

        # Process data (always force reprocess for new recipes)
        dataset = load_or_process_data(params, recipe_name, ref_steps)

        print(f"Completed data generation")
        print(f"   Data shape: {dataset.data.shape}")
        print(f"   Saved to: {params.save_path(recipe_name)}")

        return dataset

    except Exception as e:
        print(f"Error in data generation: {str(e)}")
        raise
    finally:
        # Only close client if we created it (not provided by caller)
        if should_close_client:
            close_dask_client(client)


def main(recipe: dict, recipe_name: str = None):
    """
    Main execution function for data generation from recipe.

    Args:
        recipe: Recipe dictionary from JSON file
        recipe_name: Optional recipe name for unique path generation
    """
    print("XRD DATA GENERATOR v3.0")
    print("=" * 60)
    print("Generating XRD data from recipe...")
    print(f"Sample: {recipe.get('sample', 'Unknown')}")
    print(f"Stage: {recipe.get('stage', 'Unknown')}")
    print(f"Setting: {recipe.get('setting', 'Unknown')}")
    print(f"Peaks: {[peak['name'] for peak in recipe.get('active_peaks', [])]}")
    print()

    # Generate data
    dataset = generate_data_from_recipe(recipe, recipe_name)

    # Report results
    if dataset:
        print("\nGENERATION SUMMARY:")
        print(f"   Sample: {dataset.params.sample}")
        print(f"   Stage: {dataset.params.stage.name}")
        print(f"   Peaks: {len(dataset.params.active_peaks)} active")
        print(f"   Shape: {dataset.data.shape}")
        print(f"   Zarr file: {dataset.params.save_path(recipe_name)}")
    else:
        print("\nDataset generation failed")
        print("   Check input parameters and file paths")


# ================== COMMAND LINE INTERFACE ==================

if __name__ == "__main__":
    """Command line entry point for data generation."""
    if len(sys.argv) < 2:
        print("Error: No recipe file specified.")
        print("Usage: python data_generator.py <recipe.json>")
        sys.exit(1)

    # Load recipe from file
    recipe_file = sys.argv[1]
    try:
        recipe = load_recipe_from_file(recipe_file)
        print(f"Loaded recipe from: {recipe_file}")
    except Exception as e:
        print(f"Error loading recipe file {recipe_file}: {e}")
        sys.exit(1)

    # Run data generation
    try:
        # Extract recipe name from file path
        recipe_name = os.path.basename(recipe_file)
        main(recipe, recipe_name)
        print("\nData generation completed successfully!")
    except Exception as e:
        print(f"\nData generation failed: {e}")
        sys.exit(1)