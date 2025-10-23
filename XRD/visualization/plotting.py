"""
XRD Plotting Functions Module
==============================
Heatmap drawing functions and visualization utilities for XRD data analysis.
Contains all matplotlib/seaborn plotting logic separated from high-level
visualization orchestration.

Author(s): Adrian Guzman, William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os
import openpyxl


def prepare_heatmap_data(dataset, peak_idx: int, measurement: str,
                        in_situ: bool, values: dict) -> pd.DataFrame:
    """
    Prepare data for heatmap visualization from XRDDataset.
    Creates a properly pivoted DataFrame for a single peak.

    Enhanced: Handles delta, diff, and abs measurement variants

    Args:
        dataset: XRDDataset containing the data
        peak_idx: Index of the peak to visualize
        measurement: Measurement type (may include delta, diff, abs prefixes)
        in_situ: True for time-based (continuous), False for depth-based
        values: User settings dictionary

    Returns:
        pd.DataFrame: Pivoted data ready for heatmap (frames/time x azimuths)
    """
    # Import here to avoid circular imports
    from XRD.visualization.data_visualization import process_measurement_type

    # Process measurement type (handle delta, diff, abs variants)
    processed_measurement, was_calculated = process_measurement_type(dataset, measurement)

    if was_calculated:
        print(f"Calculated {processed_measurement} from {measurement}")

    # Validate processed measurement exists
    if processed_measurement not in dataset.col_idx:
        raise ValueError(f"Measurement '{processed_measurement}' not found in dataset. Available: {list(dataset.col_idx.keys())}")

    # Get data for the specified peak and processed measurement
    col_idx = dataset.col_idx[processed_measurement]

    # Ensure data is finalized if using the fixed XRDDataset
    if hasattr(dataset, 'finalize') and dataset.data is None:
        dataset.finalize()

    # Extract the 2D slice: frames x azimuths for this peak and measurement
    value_data = dataset.data[peak_idx, :, :, col_idx].compute()  # 2D array: frames x azimuths
    frames = dataset.frame_numbers[peak_idx, :].compute()         # 1D array: frames
    azimuths = dataset.azimuth_angles[peak_idx, :].compute()      # 1D array: azimuths

    # Remove invalid azimuths (unfilled slots marked as exactly -999 or large negative)
    # Note: 0.0 degrees is a valid azimuth angle and should NOT be filtered
    valid_az_mask = np.abs(azimuths) < 900  # Keep all reasonable angles including 0.0
    azimuths = azimuths[valid_az_mask]
    value_data = value_data[:, valid_az_mask]

    # Remove any zero frames (unfilled slots)
    valid_frame_mask = frames != 0
    # Keep first frame even if it's 0 (frame 0 is valid)
    if len(frames) > 0 and frames[0] == 0:
        valid_frame_mask[0] = True
    frames = frames[valid_frame_mask]
    value_data = value_data[valid_frame_mask, :]

    # Convert frame numbers based on data type
    if in_situ:
        # Convert to time in minutes
        time_values = (frames * 0.02) / 60
        df_index = time_values
    else:
        # Convert to depth - reverse order
        depth_values = np.arange(len(frames)-1, -1, -1)
        df_index = depth_values

    # Create DataFrame directly from 2D array
    # Rows = frames/time/depth, Columns = azimuths
    df = pd.DataFrame(value_data, index=df_index, columns=azimuths)

    # Remove columns (azimuths) that are all NaN or zero
    df = df.loc[:, (df != 0).any(axis=0)]

    # Remove rows (frames) that are all NaN or zero
    df = df.loc[(df != 0).any(axis=1)]

    # Sort by index to ensure proper ordering
    df = df.sort_index()

    # Sort columns (azimuths) to ensure proper ordering
    df = df.reindex(sorted(df.columns), axis=1)

    print(f"Prepared heatmap data: shape {df.shape}, non-zero values: {np.count_nonzero(df.values)}")

    return df


def draw_heatmap(data: pd.DataFrame, params, values: dict):
    """
    Create and save heatmap visualization.

    Args:
        data: 2D data matrix (pivoted dataframe)
        params: Graph parameters (GraphParams object)
        values: User settings from interface
    """
    if data.empty:
        print(f"No data to plot for {params.label} on peak {params.peak_miller}")
        return

    # Set up figure based on COF plotting option
    if values.get("plot_with_cof", False):
        # Load and process COF data
        cof_data = load_cof_data(values)
        fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(10, 6),
                              gridspec_kw={'width_ratios': [0.5, 2]})

        # Plot COF data
        ax[0].scatter(cof_data['cof'], cof_data['time'], s=10)
        ax[0].set_title("COF Data")
        ax[0].set_xlabel("COF")
        ax[0].set_ylabel("Time (min)")
        ax[0].margins(0)
        ax[0].invert_yaxis()
        ax[0].set_ylim(data.index[-1], data.index[0])

        heatmap_ax = ax[1]
    else:
        plt.figure(figsize=(10, 8))
        plt.rcParams.update({'font.size': 20})
        heatmap_ax = plt.gca()

    # Create heatmap based on selected mode
    tag = create_heatmap_plot(data, params, values, heatmap_ax)

    # Configure plot appearance
    configure_plot_appearance(data, params, values, heatmap_ax)

    # Save figure
    save_figure(data, params, values, tag)


def create_heatmap_plot(data: pd.DataFrame, params, values: dict, ax) -> str:
    """
    Create the actual heatmap plot and return tag for filename.

    Args:
        data: 2D data matrix
        params: Graph parameters (GraphParams object)
        values: User settings
        ax: Matplotlib axis object

    Returns:
        str: Tag string for filename generation
    """
    # Import here to avoid circular imports
    from XRD.visualization.data_visualization import GraphSetting

    cbar_kwargs = {"shrink": 0.75} if not values.get("plot_with_cof", False) else {}

    # Handle potential gaps in data
    mask = data.isna()

    if params.graph_type == GraphSetting.ROBUST_LL:
        sns.heatmap(data, cmap=values["Color"], robust=True, ax=ax,
                   vmin=params.locked_lims[0], vmax=params.locked_lims[1],
                   cbar_kws=cbar_kwargs, mask=mask)
        return "-LockedLimitsRobust"

    elif params.graph_type == GraphSetting.STANDARD:
        sns.heatmap(data, cmap=values["Color"], ax=ax, cbar_kws=cbar_kwargs)
        return "-Standard"

    elif params.graph_type == GraphSetting.STANDARD_LL:
        sns.heatmap(data, vmin=params.locked_lims[0], vmax=params.locked_lims[1],
                   cmap=values["Color"], ax=ax, cbar_kws=cbar_kwargs)
        return "-LockedLimitsStandard"

    else:  # ROBUST
        sns.heatmap(data, cmap=values["Color"], robust=True, ax=ax,
                   cbar_kws=cbar_kwargs)
        return "-Robust"


def configure_plot_appearance(data: pd.DataFrame, params, values: dict, ax):
    """
    Configure plot labels, ticks, and appearance.

    Args:
        data: 2D data matrix
        params: Graph parameters (GraphParams object)
        values: User settings
        ax: Matplotlib axis object
    """
    # Stage name conversion for titles
    convert = {'BEF': "Before", 'AFT': 'After', 'CONT': 'Continuous', 'DELT': 'Delta'}

    # Set axis labels
    ax.set_xlabel('Azimuthal Angle (degrees)')
    if not values.get("plot_with_cof", False):
        if params.in_situ:
            ax.set_ylabel('Time (min)')
        else:
            ax.set_ylabel('Depth (μm)')
    else:
        ax.set_ylabel(None)

    # Add borders to plot
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor('black')
        spine.set_linewidth(1.5 if not values.get("plot_with_cof", False) else 0.75)

    # Configure colorbar
    cbar = ax.collections[0].colorbar
    cbar.outline.set_edgecolor('black')
    cbar.outline.set_linewidth(1.5 if not values.get("plot_with_cof", False) else 0.75)

    # Set colorbar label and title based on data type
    set_colorbar_and_title(params, convert, cbar, ax, values)

    # Configure axis ticks
    configure_axis_ticks(data, params, values, ax)


def set_colorbar_and_title(params, convert: dict, cbar, ax, values: dict):
    """
    Set colorbar label and plot title.

    Args:
        params: Graph parameters (GraphParams object)
        convert: Dictionary mapping stage names to display names
        cbar: Matplotlib colorbar object
        ax: Matplotlib axis object
        values: User settings
    """
    if params.label.startswith("delta"):
        cbar.set_label(f"Δ {params.label.split()[-1].capitalize()}")
        title = f"{params.loc.name.capitalize()} Change in {params.label.split()[-1].capitalize()} " \
                f"{params.sample} {params.stage.name} {params.peak_miller} Peak ({params.graph_type.name})"

    elif params.label.startswith("diff"):
        cbar.set_label(f"Δ {params.label.split()[-1].capitalize()}")
        title = f"Difference in {params.label.split()[-1].capitalize()} ({params.peak_miller})"

    elif params.label.startswith('gamma'):
        cbar.set_label("FWHM (centidegrees)")
        title = f"{convert[params.stage.name]} ({params.peak_miller})"

    else:
        cbar.set_label(f"{params.label.capitalize()}")
        title = f"{convert[params.stage.name]} ({params.peak_miller})"

    if values.get("plot_with_cof", False):
        ax.set_title(title)
    else:
        ax.set_title(title, y=1.05)


def configure_axis_ticks(data: pd.DataFrame, params, values: dict, ax):
    """
    Configure x and y axis ticks.

    Args:
        data: 2D data matrix
        params: Graph parameters (GraphParams object)
        values: User settings
        ax: Matplotlib axis object
    """
    # Configure x-axis ticks (azimuthal angle)
    azimuths = np.array(data.columns, dtype=float)
    az_min, az_max = params.ranges

    # Calculate appropriate tick spacing to prevent overlap
    # Use adaptive spacing based on angle range, always include 0
    angle_range = az_max - az_min
    if angle_range > 270:
        tick_spacing = 60  # Full circle or near-full: 60° spacing
    elif angle_range > 180:
        tick_spacing = 45  # Wide range: 45° spacing
    else:
        tick_spacing = 30  # Standard range: 30° spacing

    # Build tick list
    start = ((az_min + tick_spacing - 1) // tick_spacing) * tick_spacing
    end = (az_max // tick_spacing) * tick_spacing
    x_ticks = list(np.arange(start, end + 1, tick_spacing))

    # Ensure 0 is included if it's within the azimuth range
    if az_min <= 0 <= az_max and 0 not in x_ticks:
        x_ticks.append(0)
        x_ticks.sort()

    # Add final boundary tick at az_max if not already included
    if az_max not in x_ticks and abs(x_ticks[-1] - az_max) > tick_spacing / 2:
        x_ticks.append(az_max)

    # Find closest data points to desired ticks and build labels
    x_tick_indices = []
    x_tick_labels = []
    for tick in x_ticks:
        if tick >= azimuths.min() and tick <= azimuths.max():
            idx = np.abs(azimuths - tick).argmin()
            x_tick_indices.append(idx)
            # Use the ideal tick value for the label, not the actual data value
            x_tick_labels.append(f"{int(tick)}")

    ax.set_xticks(x_tick_indices)
    ax.set_xticklabels(x_tick_labels, rotation=0, fontsize=10)

    # Set x-axis limits with small margin
    if not values.get("plot_with_cof", False):
        ax.set_xlim(-1.5, data.shape[1] + 1.5)
    else:
        ax.margins(0)

    # Configure y-axis ticks based on data type
    if params.in_situ:
        # Time-based: 15 evenly spaced ticks
        y_ticks = np.linspace(0, len(data.index) - 1, 15, dtype=int)
        ax.set_yticks(y_ticks)
        ax.set_yticklabels([f"{data.index[i]:.2f}" for i in y_ticks])

        if not values.get("plot_with_cof", False):
            plt.subplots_adjust(left=0.17, right=0.90, top=0.98, bottom=0.01)
        else:
            plt.tight_layout()

    else:
        # Depth-based: ticks every 20 μm
        y_ticks = np.arange(0, len(data.index), 20)
        offset = len(data.index) - y_ticks[-1] if len(y_ticks) > 0 else 0
        ax.set_yticks(np.flip(y_ticks + offset))
        ax.set_yticklabels([f"{i:.0f}" for i in y_ticks])

        if params.label.startswith("strain"):
            plt.subplots_adjust(left=0.14, right=0.88, top=0.98, bottom=0.01)
        else:
            plt.subplots_adjust(left=0.14, right=0.93, top=0.98, bottom=0.01)

    # Set aspect ratio for square pixels if not using COF
    if not values.get("plot_with_cof", False):
        ratio = ((float(values["Az End"]) - float(values["Az Start"])) / values["spacing"]) / len(data.index)
        ax.set_aspect(ratio)


def load_cof_data(values: dict) -> dict:
    """
    Load COF (Coefficient of Friction) data from Excel file.

    Args:
        values: Dictionary containing 'cof_data_file' key with path to Excel file

    Returns:
        dict: Dictionary with 'time' and 'cof' keys containing data arrays
    """
    cof_file = values["cof_data_file"]
    sheet_name = 'Average Data'
    first_column_name = 'Time(min)'
    second_column_name = 'COF'

    wb = openpyxl.load_workbook(cof_file, data_only=True)
    sheet = wb[sheet_name]

    # Identify highlighted rows
    highlighted_rows = []
    for row in sheet.iter_rows():
        for cell in row:
            if cell.fill.start_color.index != '00000000':
                highlighted_rows.append(cell.row)
                break

    if len(highlighted_rows) < 2:
        raise ValueError("There must be at least two highlighted rows to define a range.")

    # Define the start and end indices based on highlighted rows
    start_index = highlighted_rows[0] - 2
    end_index = highlighted_rows[-1] - 1

    # Read the Excel file into a DataFrame
    dfcof = pd.read_excel(cof_file, sheet_name=sheet_name)

    # Filter both columns between the highlighted rows
    filtered_time = dfcof.loc[start_index:end_index, first_column_name]
    filtered_cof = dfcof.loc[start_index:end_index, second_column_name]

    return {'time': filtered_time, 'cof': filtered_cof}


def save_figure(data: pd.DataFrame, params, values: dict, tag: str):
    """
    Save the figure and optionally the CSV data using new Analysis structure.

    Args:
        data: 2D data matrix to save as CSV (optional)
        params: Graph parameters (GraphParams object)
        values: User settings
        tag: Tag string for filename mode identification
    """
    from XRD.utils.path_manager import (get_analysis_path, generate_analysis_filename,
                              ensure_directory_exists, update_analysis_metadata)

    # Get home directory and dataset info from values
    home_dir = values.get('home_dir', os.getcwd())
    dataset_id = values.get('dataset_id', None)
    zarr_path = values.get('zarr_path', 'unknown')

    # Determine save directory: {home_dir}/Analysis/{DateStamp}/{Sample}/
    save_dir = get_analysis_path(home_dir, params.sample)
    ensure_directory_exists(save_dir)

    # Determine graph mode string from tag
    graph_mode_map = {
        '-LockedLimitsRobust': 'RobustLL',
        '-Standard': 'Standard',
        '-LockedLimitsStandard': 'StandardLL',
        '-Robust': 'Robust'
    }
    graph_mode = graph_mode_map.get(tag, 'Standard')

    # Get color mode from values
    color_mode = values.get('Color', 'Viridis')

    # Get 2θ limits if locked limits mode is used
    # Use 2θ limits from dataset params, not strain limits from UI
    locked_lims = None
    if 'LL' in graph_mode and 'theta_limits' in values:
        locked_lims = values['theta_limits']  # (lower_2θ, upper_2θ)

    # Get frame range from dataset params - ALWAYS include in filename
    frame_range = values.get('frame_range', None)

    # Get peak name and miller index
    peak_name = params.label.split()[0] if ' ' in params.label else params.label
    peak_miller = str(params.peak_miller)

    # Generate filename using new convention with identifiers
    filename_png = generate_analysis_filename(
        peak_name=peak_name,
        peak_miller=peak_miller,
        graph_mode=graph_mode,
        color_mode=color_mode,
        locked_lims=locked_lims,  # 2θ limits, not strain limits
        frame_range=frame_range,  # Always included
        dataset_id=dataset_id,
        timestamp=None,  # Generate new timestamp
        extension="tiff"
    )

    filename_csv = filename_png.replace(".tiff", ".csv")

    # Save figure
    if values.get("plot_with_cof", False):
        save_path = os.path.join(save_dir, filename_png.replace(".tiff", "-COF.tiff"))
    else:
        save_path = os.path.join(save_dir, filename_png)

    plt.savefig(save_path, format='tiff', dpi=300)

    # Save CSV if requested
    if values.get("save_csv", False):
        csv_path = os.path.join(save_dir, filename_csv)
        data.to_csv(csv_path)

    # Update metadata to link back to source dataset
    if dataset_id:
        update_analysis_metadata(save_dir, dataset_id, zarr_path, filename_png)

    plt.close()

    print(f"Saved: {filename_png}")
