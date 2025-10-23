"""
XRD Data Visualization Module
=============================
Pure visualization module for creating heatmap visualizations from XRD datasets.
Works exclusively with pre-generated Zarr data files.

Main Features:
- Direct integration with XRDDataset loaded from Zarr files
- Multiple visualization modes (Standard, Robust, Locked Limits)
- Support for in-situ (time-based) and ex-situ (depth-based) data
- Before/after comparisons and difference maps
- COF integration support
- No data processing - visualization only

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import pandas as pd
import numpy as np
import json
import os
import glob
import sys
from dataclasses import dataclass
from enum import Enum

# Import data structures only (no processing functions)
from XRD.core.gsas_processing import XRDDataset, Stages

# Import plotting functions from separate module
from XRD.visualization.plotting import (
    prepare_heatmap_data,
    draw_heatmap,
    create_heatmap_plot,
    configure_plot_appearance,
    load_cof_data,
    save_figure
)


# ================== CONFIGURATION ENUMS ==================

class GraphSetting(Enum):
    """Available graph visualization modes."""
    STANDARD = 0
    OLD_STANDARD = 1
    ROBUST = 2
    ROBUST_LL = 3
    STANDARD_LL = 4


class Location(Enum):
    """Data location specifiers."""
    DIRECT = 0
    SURROUNDING = 1
    FULL = 2


# ================== PARAMETER DATACLASS ==================

@dataclass
class GraphParams:
    """Parameters for graph generation."""
    graph_type: GraphSetting
    locked_lims: tuple[float, float]

    peak_index: int
    peak_miller: int
    label: str
    sample: str = ""
    stage: Stages = Stages.CONT
    in_situ: bool = False
    loc: Location = Location.FULL
    ranges: tuple[int, int] = (-90, 90)


# ================== VISUALIZATION FUNCTIONS ==================

def process_measurement_type(dataset: XRDDataset, measurement: str):
    """
    Process measurement type to handle delta, diff, and abs variants.

    Args:
        dataset: XRDDataset containing the data
        measurement: Measurement type (may include delta, diff, abs prefixes)

    Returns:
        Tuple of (processed_measurement_name, needs_calculation)
    """
    measurement = measurement.strip()

    # Handle delta calculations (frame-to-frame changes)
    if measurement.startswith("delta "):
        base_measurement = measurement[6:]  # Remove "delta " prefix
        if base_measurement in dataset.col_idx:
            # Calculate delta if not already present
            delta_name = f"delta_{base_measurement}"
            if delta_name not in dataset.col_idx:
                try:
                    dataset.calculate_delta(base_measurement)
                    return delta_name, True
                except Exception as e:
                    print(f"Warning: Could not calculate delta for {base_measurement}: {e}")
                    return base_measurement, False
            return delta_name, False
        else:
            print(f"Warning: Base measurement '{base_measurement}' not found for delta calculation")
            return base_measurement, False

    # Handle absolute values
    elif measurement.startswith("abs "):
        base_measurement = measurement[4:]  # Remove "abs " prefix
        if base_measurement in dataset.col_idx:
            abs_name = f"abs_{base_measurement}"
            if abs_name not in dataset.col_idx:
                # Calculate absolute values
                try:
                    base_data = dataset.get_measurement(base_measurement)
                    abs_data = np.abs(base_data)
                    dataset.add_measurement(abs_name, abs_data)
                    return abs_name, True
                except Exception as e:
                    print(f"Warning: Could not calculate absolute values for {base_measurement}: {e}")
                    return base_measurement, False
            return abs_name, False
        else:
            return base_measurement, False

    # Handle difference calculations (dataset-to-dataset)
    elif measurement.startswith("diff "):
        base_measurement = measurement[5:]  # Remove "diff " prefix
        diff_name = f"diff_{base_measurement}"
        if diff_name in dataset.col_idx:
            return diff_name, False
        else:
            print(f"Warning: Difference measurement '{diff_name}' not found. Use subtract_datasets() first.")
            return base_measurement, False

    # Standard measurement
    else:
        return measurement, False


def create_visualization(dataset: XRDDataset, graph_params: GraphParams, values: dict):
    """
    Main visualization function that creates heatmap from XRDDataset.

    Args:
        dataset: XRDDataset containing the data
        graph_params: Visualization parameters
        values: User settings
    """
    # Determine if data is in-situ based on stage
    if dataset.params.stage in (Stages.CONT, Stages.DELTDSPACING):
        graph_params.in_situ = True

    # Update graph parameters with dataset info
    graph_params.sample = dataset.params.sample
    graph_params.stage = dataset.params.stage

    # Add dataset processing parameters to values for filename generation
    if hasattr(dataset.params, 'limits'):
        values['theta_limits'] = dataset.params.limits  # 2θ limits for filename
    if hasattr(dataset.params, 'frames'):
        values['frame_range'] = dataset.params.frames  # Frame range for filename

    # Prepare data for heatmap
    heatmap_data = prepare_heatmap_data(
        dataset,
        graph_params.peak_index,
        graph_params.label,
        graph_params.in_situ,
        values
    )

    if heatmap_data.empty:
        print(f"No data available for peak {graph_params.peak_index}, measurement {graph_params.label}")
        return

    # Generate visualization
    draw_heatmap(heatmap_data, graph_params, values)


# ================== MAIN EXECUTION FUNCTION ==================

def visualize_from_zarr(zarr_path: str, values: dict):
    """
    Create visualizations from existing Zarr dataset.

    Args:
        zarr_path: Path to Zarr dataset directory
        values: Dictionary of visualization settings
    """
    try:
        # Load dataset from Zarr
        print(f"Loading dataset from: {zarr_path}")
        dataset = XRDDataset.load(zarr_path)

        # Extract home_dir from dataset params and add to values
        if hasattr(dataset.params, 'home_dir'):
            values['home_dir'] = dataset.params.home_dir
        else:
            values['home_dir'] = os.getcwd()  # Fallback

        # Generate dataset ID for traceability
        if hasattr(dataset.params, 'get_dataset_id'):
            values['dataset_id'] = dataset.params.get_dataset_id()
        else:
            # Fallback: generate from zarr path
            import hashlib
            values['dataset_id'] = hashlib.md5(zarr_path.encode()).hexdigest()[:8]

        values['zarr_path'] = zarr_path

        # Parse map types
        label_vals = [label.strip() for label in values["Map_Type"].split(",")]

        # Convert graph mode to enum
        mode_mapping = {
            "Robust L.L.": "ROBUST_LL",
            "Standard L.L.": "STANDARD_LL"
        }
        graph_input = mode_mapping.get(values["Mode"], values["Mode"].upper())
        graph_type = GraphSetting[graph_input]

        # Create graph parameters
        graph_params = GraphParams(
            graph_type=graph_type,
            locked_lims=values.get("Locked Limits", (0.0, 0.0)),
            peak_index=0,  # Will be updated in loop
            peak_miller=200,  # Will be updated in loop
            label="placeholder",  # Will be updated in loop
            sample=dataset.params.sample,
            stage=dataset.params.stage,
            in_situ=(dataset.params.stage == Stages.CONT),
            loc=Location.FULL,
            ranges=(-90, 90)  # Default range
        )

        # Create visualizations for each measurement type
        for label in label_vals:
            graph_params.label = label

            # Generate for all peaks
            for peak_idx, peak_miller in [(0, 110), (1, 200), (2, 211)]:
                graph_params.peak_index = peak_idx
                graph_params.peak_miller = peak_miller

                print(f"Creating visualization: {label} - Peak {peak_miller}")
                create_visualization(dataset, graph_params, values)

        print("Visualization complete!")

    except Exception as e:
        print(f"Error in visualization: {str(e)}")
        raise


def main(values: dict):
    """
    Main execution function for visualization from Zarr files.
    This function is maintained for backward compatibility.

    Args:
        values: Dictionary with zarr_path and visualization settings
    """
    if "zarr_path" in values:
        # Direct Zarr path provided
        visualize_from_zarr(values["zarr_path"], values)
    else:
        # Try to find matching Zarr files using new structure
        print("Searching for Zarr datasets...")

        home_dir = values.get("home_dir", os.getcwd())
        sample = values.get("sample", "")

        # Import path scanning function
        from XRD.utils.path_manager import find_zarr_datasets

        # Find datasets
        found_datasets = find_zarr_datasets(home_dir, sample=sample if sample else None)

        if not found_datasets:
            raise FileNotFoundError(
                f"No datasets found for sample '{sample}' in {home_dir}/Processed/. "
                "Generate data first using batch processor."
            )

        print(f"Found {len(found_datasets)} dataset(s)")

        # Process found datasets
        for dataset_info in found_datasets:
            zarr_path = dataset_info['path']
            print(f"Processing: {dataset_info['sample']} - {dataset_info['date']} - {dataset_info['params_string']}")
            visualize_from_zarr(zarr_path, values)


def create_visualizations_from_datasets(datasets: list, values: dict):
    """
    Create visualizations from multiple loaded datasets.
    Useful for difference calculations and comparisons.

    Args:
        datasets: List of XRDDataset objects
        values: Visualization parameters
    """
    # Parse map types
    label_vals = [label.strip() for label in values["Map_Type"].split(",")]

    # Create visualizations for each dataset
    for dataset in datasets:
        # Convert graph mode to enum
        mode_mapping = {
            "Robust L.L.": "ROBUST_LL",
            "Standard L.L.": "STANDARD_LL"
        }
        graph_input = mode_mapping.get(values["Mode"], values["Mode"].upper())
        graph_type = GraphSetting[graph_input]

        # Create graph parameters
        graph_params = GraphParams(
            graph_type=graph_type,
            locked_lims=values.get("Locked Limits", (0.0, 0.0)),
            peak_index=0,
            peak_miller=200,
            label="placeholder",
            sample=dataset.params.sample,
            stage=dataset.params.stage,
            in_situ=(dataset.params.stage == Stages.CONT),
            loc=Location.FULL,
            ranges=(-90, 90)
        )

        # Generate visualizations
        for label in label_vals:
            graph_params.label = label

            for peak_idx, peak_miller in [(0, 110), (1, 200), (2, 211)]:
                graph_params.peak_index = peak_idx
                graph_params.peak_miller = peak_miller
                create_visualization(dataset, graph_params, values)


# ================== COMMAND LINE INTERFACE ==================

if __name__ == "__main__":
    """Command line entry point."""
    if len(sys.argv) < 2:
        print("Error: No data received.")
        print("Usage: python data_visualization.py '<json_string>'")
        sys.exit(1)

    # Get JSON string from command line
    values_json = sys.argv[1]

    # Parse JSON to dictionary
    try:
        values = json.loads(values_json)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        sys.exit(1)

    # Run main function
    main(values)
