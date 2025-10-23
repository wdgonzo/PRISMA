#!/usr/bin/env python3
"""
Automatic GSAS-II Calibration Module
=====================================
Performs multi-distance calibration on standard reference materials (Ceria, Si, etc.)
and generates .imctrl calibration files for use in XRD data processing.

Based on GSAS-II imageMultiDistCalib() example from documentation.

Key Features:
- Multi-distance calibration for improved accuracy
- Iterative refinement until convergence
- Automatic calibration file naming for reuse
- Support for multiple calibrant materials

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import os
import glob
import G2script as G2sc
from typing import Tuple, Dict, Optional


def generate_calibration_filename(
    setting: str,
    wavelength: float,
    pixel_size: Tuple[float, float]
) -> str:
    """
    Generate consistent calibration filename for reuse.

    Args:
        setting: Detector setting name (e.g., "1x50", "Profile")
        wavelength: X-ray wavelength in Angstroms
        pixel_size: Pixel size tuple (x, y) in microns

    Returns:
        Calibration filename in format: {setting}_{wavelength}A_{pixel_size}um.imctrl

    Example:
        >>> generate_calibration_filename("1x50", 0.240, (172, 172))
        "1x50_0.240A_172um_calibrated.imctrl"
    """
    return f"{setting}_{wavelength:.3f}A_{int(pixel_size[0])}um_calibrated.imctrl"


def perform_calibration(
    ceria_folder: str,
    pixel_size: Tuple[float, float],
    wavelength: float,
    detector_size: Tuple[int, int],
    calibrant: str = "CeO2",
    initial_params: Optional[Dict] = None,
    output_path: Optional[str] = None,
    setting_name: str = "calibration"
) -> str:
    """
    Perform multi-distance GSAS-II calibration on standard material images.

    This function implements the GSAS-II imageMultiDistCalib() workflow:
    1. Load all calibration images into a G2Project
    2. Set initial detector parameters
    3. Set calibrant and refinement parameters
    4. Perform initial single-image calibrations
    5. Run multi-distance global calibration
    6. Iteratively refine until convergence (delta < ringpicks/10)
    7. Save .imctrl file

    Args:
        ceria_folder: Path to folder containing calibration .tif images
        pixel_size: Detector pixel size (x, y) in microns
        wavelength: X-ray wavelength in Angstroms
        detector_size: Detector dimensions (x, y) in pixels
        calibrant: Standard material name (default: "CeO2")
                  Options: "CeO2", "Si    SRM640c", "LaB6", etc.
        initial_params: Dict with starting values:
                       - center: [x, y] beam center in pixels
                       - pixLimit: Max pixel error (default: 2)
                       - cutoff: Peak intensity cutoff (default: 5.0)
                       - DetDepth: Detector depth in cm (default: 0.03)
                       - calibdmin: Minimum d-spacing in Angstroms (default: 0.5)
        output_path: Where to save .imctrl file (default: ceria_folder)
        setting_name: Setting name for filename generation

    Returns:
        Path to generated .imctrl calibration file

    Raises:
        FileNotFoundError: If no .tif images found in ceria_folder
        RuntimeError: If calibration fails to converge
    """

    # Set default initial parameters
    if initial_params is None:
        initial_params = {
            'wavelength': wavelength,
            'center': [detector_size[0] / 2.0, detector_size[1] / 2.0],  # Center of detector
            'pixLimit': 2,
            'cutoff': 5.0,
            'DetDepth': 0.03,  # 0.3 mm typical for Pilatus
            'calibdmin': 0.5
        }
    else:
        # Ensure wavelength is set from parameter
        initial_params['wavelength'] = wavelength

    # Set output path
    if output_path is None:
        output_path = ceria_folder

    os.makedirs(output_path, exist_ok=True)

    # Create temporary G2Project for calibration
    temp_gpx_path = os.path.join(output_path, f'{setting_name}_calibration.gpx')
    print(f"\n{'='*60}")
    print(f"Starting GSAS-II Multi-Distance Calibration")
    print(f"{'='*60}")
    print(f"Calibrant: {calibrant}")
    print(f"Wavelength: {wavelength} Å")
    print(f"Pixel size: {pixel_size} μm")
    print(f"Detector size: {detector_size} pixels")
    print(f"Initial center: {initial_params['center']}")

    gpx = G2sc.G2Project(newgpx=temp_gpx_path)

    # Load all .tif images from calibration folder
    tif_files = glob.glob(os.path.join(ceria_folder, '*.tif'))
    if not tif_files:
        raise FileNotFoundError(f"No .tif images found in {ceria_folder}")

    print(f"\nLoading {len(tif_files)} calibration images...")
    for tif_file in sorted(tif_files):
        print(f"   {os.path.basename(tif_file)}")
        gpx.add_image(tif_file, fmthint="TIF")

    # Configure all images with initial parameters and refinement settings
    print(f"\nConfiguring calibration parameters...")
    for img in gpx.images():
        # Set calibrant material
        img.setCalibrant(calibrant)

        # Set all refinement parameters to False initially
        img.setVary('*', False)

        # Enable key refinement parameters
        # det-X, det-Y: detector position
        # phi, tilt: detector orientation
        # wave: wavelength refinement
        img.setVary(['det-X', 'det-Y', 'phi', 'tilt', 'wave'], True)

        # Apply initial control parameters
        img.setControls(initial_params)

        # Adjust calibdmin for images at different distances if needed
        if img.getControl('setdist') > 900:  # Far distance (>900 mm)
            img.setControls({'calibdmin': 1.0})

        # Perform initial single-image recalibration
        img.Recalibrate()

    # Reduce output verbosity for iteration
    G2sc.SetPrintLevel('warn')

    # First global multi-distance fit
    print(f"\nPerforming initial multi-distance calibration...")
    result, covData = gpx.imageMultiDistCalib()
    initial_ringpicks = covData['obs']
    print(f"Initial ring picks: {initial_ringpicks}")
    print(f"Refined parameters: {', '.join([f'{k}={result[k]:.4f}' for k in result if '-' not in k])}")

    # Add detector depth parameter and refine iteratively
    print(f"\nIterative refinement with detector depth...")
    for img in gpx.images():
        img.setVary('dep', True)

    ringpicks = initial_ringpicks
    delta = ringpicks
    iteration = 1
    max_iterations = 20

    while delta > ringpicks / 10 and iteration < max_iterations:
        result, covData = gpx.imageMultiDistCalib(verbose=False)
        new_ringpicks = covData['obs']
        delta = new_ringpicks - ringpicks

        print(f"Iteration {iteration}: ring picks {ringpicks:.0f} → {new_ringpicks:.0f} (Δ={delta:.0f})")

        ringpicks = new_ringpicks
        iteration += 1

    if iteration >= max_iterations:
        print(f"Warning: Reached maximum iterations ({max_iterations})")

    # Final calibration with full output
    print(f"\nFinal calibration refinement...")
    result, covData = gpx.imageMultiDistCalib(verbose=True)
    final_ringpicks = covData['obs']

    print(f"\n{'='*60}")
    print(f"Calibration Complete!")
    print(f"{'='*60}")
    print(f"Final ring picks: {final_ringpicks}")
    print(f"Improvement: {initial_ringpicks:.0f} → {final_ringpicks:.0f} ({initial_ringpicks-final_ringpicks:.0f} picks)")
    print(f"\nRefined parameters:")
    for key in sorted(result.keys()):
        if '-' not in key:  # Global parameters only
            print(f"   {key}: {result[key]:.6f}")

    # Save image control files
    print(f"\nSaving calibration files...")
    calibration_file = None
    for img in gpx.images():
        # Save control file for each image
        img_name = os.path.splitext(img.name)[0]
        imctrl_path = os.path.join(output_path, f"{img_name}.imctrl")
        img.saveControls(imctrl_path)
        print(f"   Saved: {os.path.basename(imctrl_path)}")

        # Use first image's calibration as the primary calibration file
        if calibration_file is None:
            calibration_file = imctrl_path

    # Create a standardized filename copy for easy reuse
    standard_filename = generate_calibration_filename(setting_name, wavelength, pixel_size)
    standard_path = os.path.join(output_path, standard_filename)

    # Copy first calibration to standard name
    import shutil
    shutil.copy(calibration_file, standard_path)
    print(f"\nStandardized calibration file:")
    print(f"   {standard_filename}")

    # Save the G2Project for reference
    gpx.save()
    print(f"\nCalibration project saved: {os.path.basename(temp_gpx_path)}")

    return standard_path


def get_or_create_calibration(
    recipe: dict,
    setting: str,
    pixel_size: Tuple[float, float],
    wavelength: float,
    detector_size: Tuple[int, int]
) -> str:
    """
    Get existing calibration file or create new one if not found.

    This function checks for an existing calibration file with the standardized
    naming convention. If found, it returns the path. If not found, it performs
    automatic calibration on the ceria images specified in the recipe.

    Args:
        recipe: Recipe dictionary containing calibration configuration
        setting: Detector setting name
        pixel_size: Pixel size tuple (x, y) in microns
        wavelength: X-ray wavelength in Angstroms
        detector_size: Detector dimensions (x, y) in pixels

    Returns:
        Path to calibration .imctrl file (existing or newly created)

    Raises:
        ValueError: If auto_calibrate is True but ceria_folder not specified
        FileNotFoundError: If ceria_folder doesn't exist
    """

    # Get calibration configuration from recipe
    calibration_config = recipe.get('calibration', {})

    if not calibration_config.get('auto_calibrate', False):
        # User doesn't want auto-calibration, return manual control file
        return recipe['control_file']

    # Check for ceria folder
    ceria_folder = calibration_config.get('ceria_folder')
    if not ceria_folder:
        raise ValueError("auto_calibrate is True but ceria_folder not specified in recipe")

    if not os.path.exists(ceria_folder):
        raise FileNotFoundError(f"Ceria calibration folder not found: {ceria_folder}")

    # Generate standardized calibration filename
    calib_filename = generate_calibration_filename(setting, wavelength, pixel_size)
    calib_path = os.path.join(ceria_folder, calib_filename)

    # Check if calibration file already exists
    if os.path.exists(calib_path):
        print(f"\n{'='*60}")
        print(f"Using existing calibration file:")
        print(f"   {calib_filename}")
        print(f"{'='*60}")
        return calib_path

    # Calibration doesn't exist, create it
    print(f"\n{'='*60}")
    print(f"No existing calibration found for:")
    print(f"   Setting: {setting}")
    print(f"   Wavelength: {wavelength} Å")
    print(f"   Pixel size: {pixel_size} μm")
    print(f"Creating new calibration...")
    print(f"{'='*60}")

    # Extract calibration parameters from recipe
    calibrant = calibration_config.get('calibrant', 'CeO2')
    initial_params = calibration_config.get('initial_params')

    # Perform calibration
    calib_path = perform_calibration(
        ceria_folder=ceria_folder,
        pixel_size=pixel_size,
        wavelength=wavelength,
        detector_size=detector_size,
        calibrant=calibrant,
        initial_params=initial_params,
        output_path=ceria_folder,
        setting_name=setting
    )

    return calib_path


# ================== CLI INTERFACE ==================

if __name__ == "__main__":
    """
    Command-line interface for standalone calibration.

    Usage:
        python calibration.py <ceria_folder> <wavelength> <pixel_size_x> <pixel_size_y> <detector_x> <detector_y>

    Example:
        python calibration.py G:/Data/Ceria 0.240 172 172 1475 1679
    """
    import sys

    if len(sys.argv) < 7:
        print("Usage: python calibration.py <ceria_folder> <wavelength> <pixel_x> <pixel_y> <detector_x> <detector_y>")
        print("\nExample:")
        print("  python calibration.py G:/Data/Ceria 0.240 172 172 1475 1679")
        sys.exit(1)

    ceria_folder = sys.argv[1]
    wavelength = float(sys.argv[2])
    pixel_size = (float(sys.argv[3]), float(sys.argv[4]))
    detector_size = (int(sys.argv[5]), int(sys.argv[6]))

    calibration_file = perform_calibration(
        ceria_folder=ceria_folder,
        pixel_size=pixel_size,
        wavelength=wavelength,
        detector_size=detector_size,
        calibrant="CeO2",
        setting_name="manual"
    )

    print(f"\n{'='*60}")
    print(f"SUCCESS!")
    print(f"Calibration file created: {calibration_file}")
    print(f"{'='*60}")
