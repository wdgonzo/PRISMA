"""
Path Manager Module
===================
Centralized path generation and management for the XRD processing system.
Handles all file and directory path construction following the new organizational structure.

Directory Structure:
    Home/
    ├── Data/{MonthYear}/{Sample}/{Stage}/{Images,Refs}/
    ├── Analysis/{DateStamp}/{Sample}/{files}
    ├── Processed/{DateStamp}/{Sample}/{Zarr,Intensity}/
    └── Params/{recipes,analyzer}/

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import os
import hashlib
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import json


# ================== DATE AND TIMESTAMP UTILITIES ==================

def get_datestamp() -> str:
    """
    Get current date in YYYY-MM-DD format.

    Returns:
        Date string in format: 2025-10-22
    """
    return datetime.now().strftime("%Y-%m-%d")


def get_timestamp() -> str:
    """
    Get current timestamp in HHMMSS format (time only, no date).

    Returns:
        Timestamp string in format: 143022
    """
    return datetime.now().strftime("%H%M%S")


def get_timestamp_for_filename() -> str:
    """
    Get timestamp suitable for use in filenames.

    Returns:
        Timestamp string in format: 143022
    """
    return get_timestamp()


# ================== FILENAME UTILITIES ==================

def format_number_for_filename(value: float) -> str:
    """
    Format a number for use in filenames, handling negatives.

    Args:
        value: Numeric value (can be negative)

    Returns:
        String representation safe for filenames
        Example: -110 -> "minus110", 90 -> "90"
    """
    if value < 0:
        return f"minus{abs(int(value))}"
    else:
        return str(int(value))


def clean_name_for_filename(name: str) -> str:
    """
    Clean a name/string for safe use in filenames.

    Args:
        name: Original name string

    Returns:
        Cleaned string with no spaces or special characters
        Example: "Martensite 211" -> "Martensite211"
    """
    # Remove spaces and problematic characters
    cleaned = name.replace(" ", "").replace("/", "-").replace("\\", "-")
    # Remove any remaining unsafe characters
    safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    cleaned = ''.join(c for c in cleaned if c in safe_chars)
    return cleaned


def generate_dataset_id(params_dict: Dict[str, Any]) -> str:
    """
    Generate a short unique ID for a dataset based on its parameters.
    Used to link analysis plots back to source datasets.

    Args:
        params_dict: Dictionary of parameters that define the dataset

    Returns:
        8-character hex string uniquely identifying this parameter set
        Example: "a1b2c3d4"
    """
    # Create a stable string representation of parameters
    param_str = json.dumps(params_dict, sort_keys=True)

    # Generate hash
    hash_obj = hashlib.md5(param_str.encode())

    # Return first 8 characters of hex digest
    return hash_obj.hexdigest()[:8]


# ================== PARAMETER STRING GENERATION ==================

def generate_zarr_params_string(total_az: int, bin_count: int,
                                 frame_start: int, frame_end: int,
                                 theta_limits: tuple[float, float],
                                 num_peaks: int, num_bkg: int,
                                 timestamp: str = None) -> str:
    """
    Generate parameter string for Zarr folder names with descriptive identifiers.

    Format: {total}deg-{bins}bins-{start}sf-{end}efr-{lower}l2t_{upper}u2t-{npeaks}peaks-{nbkg}bkg-{time}
    Example: 360deg-72bins-0sf-100efr-8.2l2t_8.8u2t-3peaks-2bkg-143022

    Args:
        total_az: Total azimuthal range in degrees
        bin_count: Number of azimuthal bins
        frame_start: Starting frame number
        frame_end: Ending frame number (-1 for all frames)
        theta_limits: 2θ analysis range (lower, upper) in degrees
        num_peaks: Number of active peaks analyzed
        num_bkg: Number of background/interference peaks
        timestamp: Optional timestamp (generates new if None)

    Returns:
        Parameter string for folder name with identifiers
    """
    if timestamp is None:
        timestamp = get_timestamp()

    # Handle -1 end frame
    efr_str = "allfr" if frame_end == -1 else f"{frame_end}efr"

    # Format 2θ limits with 1 decimal precision, units after values
    lower_2t = f"{theta_limits[0]:.1f}l2t"
    upper_2t = f"{theta_limits[1]:.1f}u2t"

    return (f"{total_az}deg-{bin_count}bins-{frame_start}sf-{efr_str}-"
            f"{lower_2t}_{upper_2t}-{num_peaks}peaks-{num_bkg}bkg-{timestamp}")


def generate_intensity_params_string(total_az: int, bin_count: int,
                                      frame_start: int, frame_end: int,
                                      theta_limits: tuple[float, float],
                                      timestamp: str = None) -> str:
    """
    Generate parameter string for Intensity folder names with descriptive identifiers.

    Note: Intensity plots are dataset-level (not per-peak), so no peak identifier included.

    Format: {total}deg-{bins}bins-{start}sf-{end}efr-{lower}l2t_{upper}u2t-{time}
    Example: 360deg-72bins-0sf-100efr-8.2l2t_8.8u2t-143022

    Args:
        total_az: Total azimuthal range in degrees
        bin_count: Number of azimuthal bins
        frame_start: Starting frame number
        frame_end: Ending frame number (-1 for all frames)
        theta_limits: 2θ analysis range (lower, upper) in degrees
        timestamp: Optional timestamp (generates new if None)

    Returns:
        Parameter string for folder name with identifiers
    """
    if timestamp is None:
        timestamp = get_timestamp()

    # Handle -1 end frame
    efr_str = "allfr" if frame_end == -1 else f"{frame_end}efr"

    # Format 2θ limits with 1 decimal precision, units after values
    lower_2t = f"{theta_limits[0]:.1f}l2t"
    upper_2t = f"{theta_limits[1]:.1f}u2t"

    return (f"{total_az}deg-{bin_count}bins-{frame_start}sf-{efr_str}-"
            f"{lower_2t}_{upper_2t}-{timestamp}")


def generate_analysis_filename(peak_name: str, peak_miller: str,
                                graph_mode: str, color_mode: str,
                                locked_lims: Optional[Tuple[float, float]] = None,
                                frame_range: Optional[Tuple[int, int]] = None,
                                dataset_id: str = None,
                                timestamp: str = None,
                                extension: str = "tiff") -> str:
    """
    Generate filename for analysis plots with descriptive identifiers.

    Format: {peakname}{miller}-{mode}-{colormap}-[{lower}l2t_{upper}u2t]-{frames}-DS{id}-{time}.{ext}
    Examples:
      - Martensite211-Robust-Viridis-allfr-DSa1b2c3d4-143022.tiff
      - Martensite211-RobustLL-Viridis-8.2l2t_8.8u2t-F50_100-DSa1b2c3d4-143022.tiff

    Args:
        peak_name: Peak name (e.g., "Martensite")
        peak_miller: Miller index (e.g., "211")
        graph_mode: Graphing mode (e.g., "Robust", "RobustLL")
        color_mode: Color map name (e.g., "Viridis", "Plasma")
        locked_lims: Optional locked 2θ limits (min, max) - only shown if non-zero
        frame_range: Frame range (start, end) - ALWAYS required
        dataset_id: Optional dataset ID for traceability
        timestamp: Optional timestamp (generates new if None)
        extension: File extension (default "tiff")

    Returns:
        Complete filename with extension
    """
    if timestamp is None:
        timestamp = get_timestamp()

    # Build base filename
    peak_str = f"{clean_name_for_filename(peak_name)}{peak_miller}"
    parts = [peak_str, graph_mode, color_mode]

    # Add locked 2θ limits if present and non-zero (units after values)
    if locked_lims and locked_lims != (0.0, 0.0):
        lower_2t = f"{locked_lims[0]:.1f}l2t"
        upper_2t = f"{locked_lims[1]:.1f}u2t"
        parts.append(f"{lower_2t}_{upper_2t}")

    # ALWAYS add frame range
    if frame_range and frame_range[1] == -1:
        # All frames
        parts.append("allfr")
    elif frame_range:
        # Specific range
        parts.append(f"F{frame_range[0]}_{frame_range[1]}")
    else:
        # Default to all frames if not specified
        parts.append("allfr")

    # Add dataset reference for traceability
    if dataset_id:
        parts.append(f"DS{dataset_id}")

    # Add timestamp
    parts.append(timestamp)

    # Join with dashes and add extension
    filename = "-".join(parts)
    return f"{filename}.{extension}"


# ================== PATH GENERATION - DATA ==================

def get_data_path(home_dir: str, month_year: str, sample: str, stage: str) -> str:
    """
    Generate path to raw data directory.

    Path: {home_dir}/Data/{MonthYear}/{Sample}/{Stage}/
    Example: /home/user/Processor/Data/Oct2025/A1/CONT/

    Args:
        home_dir: Home/root directory for the project
        month_year: Month and year (e.g., "Oct2025")
        sample: Sample name (e.g., "A1")
        stage: Stage name (e.g., "CONT", "BEF", "AFT")

    Returns:
        Full path to data directory
    """
    return os.path.join(home_dir, "Data", month_year, sample, stage)


def get_images_path(home_dir: str, month_year: str, sample: str, stage: str) -> str:
    """
    Generate path to raw images directory.

    Path: {home_dir}/Data/{MonthYear}/{Sample}/{Stage}/Images/

    Args:
        home_dir: Home/root directory
        month_year: Month and year
        sample: Sample name
        stage: Stage name

    Returns:
        Full path to images directory
    """
    return os.path.join(get_data_path(home_dir, month_year, sample, stage), "Images")


def get_refs_path(home_dir: str, month_year: str, sample: str, stage: str) -> str:
    """
    Generate path to reference images directory.

    Path: {home_dir}/Data/{MonthYear}/{Sample}/{Stage}/Refs/

    Args:
        home_dir: Home/root directory
        month_year: Month and year
        sample: Sample name
        stage: Stage name

    Returns:
        Full path to refs directory
    """
    return os.path.join(get_data_path(home_dir, month_year, sample, stage), "Refs")


# ================== PATH GENERATION - PROCESSED ==================

def get_processed_base_path(home_dir: str, sample: str, datestamp: str = None) -> str:
    """
    Generate base path for processed data.

    Path: {home_dir}/Processed/{DateStamp}/{Sample}/
    Example: /home/user/Processor/Processed/2025-10-22/A1/

    Args:
        home_dir: Home/root directory
        sample: Sample name
        datestamp: Date stamp (YYYY-MM-DD), generates current if None

    Returns:
        Base path for processed data
    """
    if datestamp is None:
        datestamp = get_datestamp()

    return os.path.join(home_dir, "Processed", datestamp, sample)


def get_zarr_path(home_dir: str, sample: str, params_string: str,
                  datestamp: str = None) -> str:
    """
    Generate path for Zarr data storage.

    Path: {home_dir}/Processed/{DateStamp}/{Sample}/Zarr/{ParamsString}/

    Args:
        home_dir: Home/root directory
        sample: Sample name
        params_string: Parameter string from generate_zarr_params_string()
        datestamp: Date stamp (YYYY-MM-DD), generates current if None

    Returns:
        Full path to Zarr storage directory
    """
    base = get_processed_base_path(home_dir, sample, datestamp)
    return os.path.join(base, "Zarr", params_string)


def get_intensity_path(home_dir: str, sample: str, params_string: str,
                       datestamp: str = None) -> str:
    """
    Generate path for intensity plot storage.

    Path: {home_dir}/Processed/{DateStamp}/{Sample}/Intensity/{ParamsString}/

    Args:
        home_dir: Home/root directory
        sample: Sample name
        params_string: Parameter string from generate_intensity_params_string()
        datestamp: Date stamp (YYYY-MM-DD), generates current if None

    Returns:
        Full path to intensity plot directory
    """
    base = get_processed_base_path(home_dir, sample, datestamp)
    return os.path.join(base, "Intensity", params_string)


# ================== PATH GENERATION - ANALYSIS ==================

def get_analysis_path(home_dir: str, sample: str, datestamp: str = None) -> str:
    """
    Generate path for analysis outputs (plots, CSVs).

    Path: {home_dir}/Analysis/{DateStamp}/{Sample}/
    Example: /home/user/Processor/Analysis/2025-10-22/A1/

    Args:
        home_dir: Home/root directory
        sample: Sample name
        datestamp: Date stamp (YYYY-MM-DD), generates current if None

    Returns:
        Full path to analysis directory
    """
    if datestamp is None:
        datestamp = get_datestamp()

    return os.path.join(home_dir, "Analysis", datestamp, sample)


def get_analysis_metadata_path(home_dir: str, sample: str, datestamp: str = None) -> str:
    """
    Generate path to analysis metadata file.

    This file links analysis outputs back to their source Zarr datasets.

    Args:
        home_dir: Home/root directory
        sample: Sample name
        datestamp: Date stamp (YYYY-MM-DD), generates current if None

    Returns:
        Full path to analysis_metadata.json file
    """
    analysis_dir = get_analysis_path(home_dir, sample, datestamp)
    return os.path.join(analysis_dir, "analysis_metadata.json")


# ================== PATH GENERATION - PARAMS ==================

def get_params_base_path(home_dir: str) -> str:
    """
    Generate base path for parameter files.

    Path: {home_dir}/Params/

    Args:
        home_dir: Home/root directory

    Returns:
        Base path for parameter storage
    """
    return os.path.join(home_dir, "Params")


def get_recipes_path(home_dir: str) -> str:
    """
    Generate path for recipe files.

    Path: {home_dir}/Params/recipes/

    Args:
        home_dir: Home/root directory

    Returns:
        Path to recipes directory
    """
    return os.path.join(get_params_base_path(home_dir), "recipes")


def get_processed_recipes_path(home_dir: str) -> str:
    """
    Generate path for processed recipe files.

    Path: {home_dir}/Params/recipes/processed/

    Args:
        home_dir: Home/root directory

    Returns:
        Path to processed recipes directory
    """
    return os.path.join(get_recipes_path(home_dir), "processed")


def get_analyzer_params_path(home_dir: str) -> str:
    """
    Generate path for analyzer parameter files.

    Path: {home_dir}/Params/analyzer/

    Args:
        home_dir: Home/root directory

    Returns:
        Path to analyzer parameters directory
    """
    return os.path.join(get_params_base_path(home_dir), "analyzer")


# ================== METADATA MANAGEMENT ==================

def update_analysis_metadata(analysis_dir: str, dataset_id: str,
                              zarr_path: str, analysis_file: str):
    """
    Update the analysis metadata file to track which datasets were used.

    Creates or updates analysis_metadata.json in the analysis directory.

    Args:
        analysis_dir: Path to analysis directory
        dataset_id: Unique dataset identifier
        zarr_path: Path to source Zarr dataset
        analysis_file: Name of analysis file created
    """
    metadata_path = os.path.join(analysis_dir, "analysis_metadata.json")

    # Load existing metadata or create new
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    else:
        metadata = {
            "created": datetime.now().isoformat(),
            "datasets": {},
            "analyses": []
        }

    # Add dataset info if not already present
    if dataset_id not in metadata["datasets"]:
        metadata["datasets"][dataset_id] = {
            "zarr_path": zarr_path,
            "first_used": datetime.now().isoformat()
        }

    # Add analysis record
    metadata["analyses"].append({
        "file": analysis_file,
        "dataset_id": dataset_id,
        "created": datetime.now().isoformat()
    })

    # Save updated metadata
    os.makedirs(analysis_dir, exist_ok=True)
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=4)


# ================== DIRECTORY CREATION UTILITIES ==================

def ensure_directory_exists(path: str) -> str:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to create

    Returns:
        The path (for chaining)
    """
    os.makedirs(path, exist_ok=True)
    return path


def create_standard_structure(home_dir: str):
    """
    Create the standard directory structure for the project.

    Creates:
        - Data/
        - Analysis/
        - Processed/
        - Params/recipes/
        - Params/recipes/processed/
        - Params/analyzer/

    Args:
        home_dir: Home/root directory for the project
    """
    directories = [
        os.path.join(home_dir, "Data"),
        os.path.join(home_dir, "Analysis"),
        os.path.join(home_dir, "Processed"),
        get_recipes_path(home_dir),
        get_processed_recipes_path(home_dir),
        get_analyzer_params_path(home_dir)
    ]

    for directory in directories:
        ensure_directory_exists(directory)

    print(f"Created standard directory structure in: {home_dir}")


# ================== PATH SCANNING UTILITIES ==================

def find_zarr_datasets(home_dir: str, sample: str = None,
                       datestamp: str = None) -> list:
    """
    Find all Zarr datasets in the processed directory.

    Args:
        home_dir: Home/root directory
        sample: Optional sample name filter
        datestamp: Optional date filter (YYYY-MM-DD)

    Returns:
        List of dictionaries with dataset information
    """
    processed_dir = os.path.join(home_dir, "Processed")

    if not os.path.exists(processed_dir):
        return []

    datasets = []

    # Iterate through date folders
    for date_folder in os.listdir(processed_dir):
        if datestamp and date_folder != datestamp:
            continue

        date_path = os.path.join(processed_dir, date_folder)
        if not os.path.isdir(date_path):
            continue

        # Iterate through sample folders
        for sample_folder in os.listdir(date_path):
            if sample and sample_folder != sample:
                continue

            zarr_base = os.path.join(date_path, sample_folder, "Zarr")
            if not os.path.exists(zarr_base):
                continue

            # Find all Zarr datasets
            for dataset_folder in os.listdir(zarr_base):
                dataset_path = os.path.join(zarr_base, dataset_folder)

                # Verify it's a valid Zarr dataset (has metadata.json)
                metadata_path = os.path.join(dataset_path, "metadata.json")
                if os.path.exists(metadata_path):
                    datasets.append({
                        "path": dataset_path,
                        "date": date_folder,
                        "sample": sample_folder,
                        "params_string": dataset_folder,
                        "metadata_path": metadata_path
                    })

    return datasets


if __name__ == "__main__":
    """Test the path manager functions."""
    print("Testing Path Manager Module")
    print("=" * 60)

    # Test datestamp and timestamp
    print(f"\nDate: {get_datestamp()}")
    print(f"Timestamp: {get_timestamp()}")

    # Test number formatting
    print(f"\nFormat -110: {format_number_for_filename(-110)}")
    print(f"Format 90: {format_number_for_filename(90)}")

    # Test name cleaning
    print(f"\nClean 'Martensite 211': {clean_name_for_filename('Martensite 211')}")

    # Test parameter strings
    zarr_params = generate_zarr_params_string(220, 44, -110, 110, 0, 100, 3)
    print(f"\nZarr params: {zarr_params}")

    intensity_params = generate_intensity_params_string(220, 44, -110, 110, 0, 100,
                                                         "Martensite", "211")
    print(f"Intensity params: {intensity_params}")

    analysis_file = generate_analysis_filename("Martensite", "211", "Robust", "Viridis",
                                                locked_lims=(0.002, 0.005),
                                                frame_range=(50, 100),
                                                dataset_id="a1b2c3d4")
    print(f"Analysis file: {analysis_file}")

    # Test path generation
    home = "/home/user/Processor"
    print(f"\n\nPath Generation Tests (home={home}):")
    print(f"Data path: {get_data_path(home, 'Oct2025', 'A1', 'CONT')}")
    print(f"Zarr path: {get_zarr_path(home, 'A1', zarr_params)}")
    print(f"Analysis path: {get_analysis_path(home, 'A1')}")
    print(f"Recipes path: {get_recipes_path(home)}")
