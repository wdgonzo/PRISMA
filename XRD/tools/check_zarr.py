"""
Zarr Data Inspection Tool
=========================
Diagnostic utility for inspecting and validating Zarr datasets.

Provides detailed information about compression, chunk sizes, data quality,
and metadata for XRD datasets stored in Zarr format.

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import zarr
import numpy as np
import json
import dask.array as da
import matplotlib.pyplot as plt
import os
from typing import Dict, List, Tuple

def analyze_compression(path: str) -> Dict:
    """Analyze compression performance and codec information"""
    compression_info = {
        'zarr_version': getattr(zarr, '__version__', 'unknown'),
        'compression_ratios': {},
        'codec_info': {},
        'file_sizes': {}
    }

    try:
        # Load main data array
        data_store = zarr.open(f"{path}/data.zarr", mode='r')

        # Get compression info from metadata
        if hasattr(data_store, 'meta'):
            # v3 metadata structure
            meta = data_store.meta
            compression_info['codec_info'] = {
                'zarr_format': getattr(meta, 'zarr_format', 'unknown'),
                'codecs': str(getattr(meta, 'codecs', 'none')),
                'chunk_shape': getattr(meta, 'chunk_grid', {}).get('chunk_shape', 'unknown')
            }
        else:
            # v2 metadata structure
            compression_info['codec_info'] = {
                'zarr_format': 2,
                'compressor': str(data_store.compressor) if hasattr(data_store, 'compressor') else 'none',
                'chunk_shape': data_store.chunks if hasattr(data_store, 'chunks') else 'unknown'
            }

        # Calculate file sizes and compression ratios
        for array_name in ['data.zarr', 'frame_numbers.zarr', 'azimuth_angles.zarr']:
            array_path = f"{path}/{array_name}"
            if os.path.exists(array_path):
                # Calculate compressed size
                compressed_size = sum(
                    os.path.getsize(os.path.join(root, file))
                    for root, dirs, files in os.walk(array_path)
                    for file in files
                )

                # Load array to calculate uncompressed size
                if array_name == 'data.zarr':
                    array = da.from_zarr(array_path)
                    uncompressed_size = array.nbytes
                elif array_name in ['frame_numbers.zarr', 'azimuth_angles.zarr']:
                    array = da.from_zarr(array_path)
                    uncompressed_size = array.nbytes
                else:
                    uncompressed_size = compressed_size  # fallback

                compression_ratio = 1 - (compressed_size / uncompressed_size) if uncompressed_size > 0 else 0

                compression_info['file_sizes'][array_name] = {
                    'compressed_mb': compressed_size / (1024*1024),
                    'uncompressed_mb': uncompressed_size / (1024*1024),
                    'compression_ratio': compression_ratio,
                    'compression_percentage': compression_ratio * 100
                }

        # Overall statistics
        total_compressed = sum(info['compressed_mb'] for info in compression_info['file_sizes'].values())
        total_uncompressed = sum(info['uncompressed_mb'] for info in compression_info['file_sizes'].values())
        overall_ratio = 1 - (total_compressed / total_uncompressed) if total_uncompressed > 0 else 0

        compression_info['overall'] = {
            'total_compressed_mb': total_compressed,
            'total_uncompressed_mb': total_uncompressed,
            'overall_compression_ratio': overall_ratio,
            'overall_compression_percentage': overall_ratio * 100
        }

    except Exception as e:
        compression_info['error'] = str(e)

    return compression_info

def validate_parameters(data: np.ndarray, measurement_cols: List[str]) -> Dict:
    """Validate peak fitting parameters for physical reasonableness"""
    validation_results = {
        'total_peaks_analyzed': 0,
        'validation_failures': {},
        'parameter_statistics': {},
        'warnings': []
    }

    # Define parameter bounds
    bounds = {
        'area': (1e-6, 1e8),
        'sigma': (0.001, 2.0),
        'gamma': (0.0, 1.0),
        'pos': (5.0, 15.0),  # Reasonable 2-theta range
        'd': (0.5, 3.0),     # Reasonable d-spacing range
        'strain': (-0.1, 0.1)  # ±10% strain is reasonable
    }

    for i, col in enumerate(measurement_cols):
        if col in bounds:
            col_data = data[:, :, :, i]
            non_zero_mask = col_data != 0
            non_zero_data = col_data[non_zero_mask]

            if len(non_zero_data) > 0:
                validation_results['total_peaks_analyzed'] += len(non_zero_data)

                # Check bounds
                min_val, max_val = bounds[col]
                out_of_bounds = np.logical_or(non_zero_data < min_val, non_zero_data > max_val)
                num_failures = np.sum(out_of_bounds)

                if num_failures > 0:
                    validation_results['validation_failures'][col] = {
                        'count': int(num_failures),
                        'percentage': float(100 * num_failures / len(non_zero_data)),
                        'min_found': float(np.min(non_zero_data)),
                        'max_found': float(np.max(non_zero_data)),
                        'expected_range': bounds[col]
                    }

                # Statistics
                validation_results['parameter_statistics'][col] = {
                    'count': int(len(non_zero_data)),
                    'mean': float(np.mean(non_zero_data)),
                    'std': float(np.std(non_zero_data)),
                    'min': float(np.min(non_zero_data)),
                    'max': float(np.max(non_zero_data)),
                    'median': float(np.median(non_zero_data))
                }

    return validation_results

def plot_parameter_distributions(data: np.ndarray, measurement_cols: List[str], save_path: str = None):
    """Plot histograms of peak fitting parameters"""
    n_cols = len(measurement_cols)
    n_rows = (n_cols + 2) // 3  # 3 columns per row

    fig, axes = plt.subplots(n_rows, 3, figsize=(15, 5*n_rows))
    if n_rows == 1:
        axes = axes.reshape(1, -1)

    for i, col in enumerate(measurement_cols):
        row = i // 3
        col_idx = i % 3
        ax = axes[row, col_idx]

        col_data = data[:, :, :, i]
        non_zero_data = col_data[col_data != 0]

        if len(non_zero_data) > 0:
            ax.hist(non_zero_data, bins=50, alpha=0.7, edgecolor='black')
            ax.set_xlabel(col)
            ax.set_ylabel('Frequency')
            ax.set_title(f'{col} Distribution\n(n={len(non_zero_data)})')
            ax.grid(True, alpha=0.3)

            # Add statistics
            mean_val = np.mean(non_zero_data)
            std_val = np.std(non_zero_data)
            ax.axvline(mean_val, color='red', linestyle='--', label=f'Mean: {mean_val:.3f}')
            ax.axvline(mean_val + std_val, color='orange', linestyle=':', alpha=0.7)
            ax.axvline(mean_val - std_val, color='orange', linestyle=':', alpha=0.7)
            ax.legend()
        else:
            ax.text(0.5, 0.5, f'No data for {col}', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{col} - No Data')

    # Hide unused subplots
    for i in range(len(measurement_cols), n_rows * 3):
        row = i // 3
        col_idx = i % 3
        axes[row, col_idx].set_visible(False)

    plt.tight_layout()

    if save_path:
        plt.savefig(f"{save_path}_parameter_distributions.png", dpi=300, bbox_inches='tight')
        print(f"Parameter distribution plots saved to {save_path}_parameter_distributions.png")
    else:
        plt.show()

    plt.close()

def analyze_peak_quality(data: np.ndarray, measurement_cols: List[str]) -> Dict:
    """Analyze the quality of peak fits"""
    quality_analysis = {
        'peak_statistics': {},
        'azimuth_coverage': {},
        'frame_coverage': {}
    }

    n_peaks, n_frames, n_azimuths, n_measurements = data.shape

    # Analyze each peak
    for peak_idx in range(n_peaks):
        peak_data = data[peak_idx]

        # Count non-zero values per measurement
        peak_stats = {}
        for i, col in enumerate(measurement_cols):
            col_data = peak_data[:, :, i]
            non_zero_count = np.count_nonzero(col_data)
            total_possible = n_frames * n_azimuths
            coverage = 100 * non_zero_count / total_possible if total_possible > 0 else 0

            peak_stats[col] = {
                'non_zero_count': int(non_zero_count),
                'coverage_percentage': float(coverage),
                'total_possible': total_possible
            }

        quality_analysis['peak_statistics'][f'peak_{peak_idx}'] = peak_stats

    # Analyze azimuth coverage
    for az_idx in range(min(10, n_azimuths)):  # Sample first 10 azimuths
        az_data = data[:, :, az_idx, :]
        non_zero_count = np.count_nonzero(az_data)
        total_possible = n_peaks * n_frames * n_measurements
        coverage = 100 * non_zero_count / total_possible if total_possible > 0 else 0
        quality_analysis['azimuth_coverage'][f'azimuth_{az_idx}'] = float(coverage)

    # Analyze frame coverage
    for frame_idx in range(min(10, n_frames)):  # Sample first 10 frames
        frame_data = data[:, frame_idx, :, :]
        non_zero_count = np.count_nonzero(frame_data)
        total_possible = n_peaks * n_azimuths * n_measurements
        coverage = 100 * non_zero_count / total_possible if total_possible > 0 else 0
        quality_analysis['frame_coverage'][f'frame_{frame_idx}'] = float(coverage)

    return quality_analysis

def inspect_zarr_data(path: str, create_plots: bool = True, save_validation_report: bool = True):
    """Inspect contents of Zarr dataset with proper Dask handling"""
    print(f"Inspecting Zarr data at: {path}")
    
    # Load metadata
    with open(f"{path}/metadata.json", 'r') as f:
        metadata = json.load(f)
        print("\nMetadata:")
        print(json.dumps(metadata, indent=2))
    
    # Load main data array as Dask array
    data = da.from_zarr(f"{path}/data.zarr")
    print("\nMain data array:")
    print(f"Shape: {data.shape}")
    print(f"Chunks: {data.chunks}")
    print(f"Data type: {data.dtype}")
    
    # Compute statistics (this will load data in chunks)
    data_computed = data.compute()  # Load into memory
    non_zero_count = np.count_nonzero(data_computed)
    print(f"Non-zero elements: {non_zero_count} / {data_computed.size} ({100*non_zero_count/data_computed.size:.2f}%)")

    # Compression analysis first
    print("\n" + "="*60)
    print("COMPRESSION PERFORMANCE ANALYSIS")
    print("="*60)

    compression_results = analyze_compression(path)

    print(f"Zarr Version: {compression_results['zarr_version']}")

    if 'error' in compression_results:
        print(f"Compression analysis failed: {compression_results['error']}")
    else:
        # Codec information
        codec_info = compression_results['codec_info']
        print(f"Zarr Format: {codec_info.get('zarr_format', 'unknown')}")

        if 'codecs' in codec_info:
            print(f"Codecs: {codec_info['codecs']}")
        if 'compressor' in codec_info:
            print(f"Compressor: {codec_info['compressor']}")

        print(f"Chunk Shape: {codec_info.get('chunk_shape', 'unknown')}")

        # Compression statistics
        overall = compression_results['overall']
        print(f"\nOVERALL COMPRESSION:")
        print(f"  Total Compressed: {overall['total_compressed_mb']:.1f} MB")
        print(f"  Total Uncompressed: {overall['total_uncompressed_mb']:.1f} MB")
        print(f"  Compression Ratio: {overall['overall_compression_percentage']:.1f}%")

        # Performance assessment
        compression_pct = overall['overall_compression_percentage']
        if compression_pct >= 85:
            print("  EXCELLENT compression (≥85%)")
        elif compression_pct >= 75:
            print("  GOOD compression (75-84%)")
        elif compression_pct >= 65:
            print("  FAIR compression (65-74%) - consider v3 upgrade")
        else:
            print("  POOR compression (<65%) - check codec configuration")

        # Per-array breakdown
        print(f"\nPER-ARRAY BREAKDOWN:")
        for array_name, stats in compression_results['file_sizes'].items():
            print(f"  {array_name}:")
            print(f"    Size: {stats['compressed_mb']:.1f} MB ({stats['compression_percentage']:.1f}% compression)")

    # Perform comprehensive validation
    print("\n" + "="*60)
    print("PARAMETER VALIDATION ANALYSIS")
    print("="*60)

    validation_results = validate_parameters(data_computed, metadata['measurement_cols'])

    if validation_results['validation_failures']:
        print("VALIDATION FAILURES DETECTED:")
        for param, failures in validation_results['validation_failures'].items():
            print(f"\n{param.upper()}:")
            print(f"  {failures['count']} values out of bounds ({failures['percentage']:.1f}%)")
            print(f"  Found range: [{failures['min_found']:.6f}, {failures['max_found']:.6f}]")
            print(f"  Expected range: {failures['expected_range']}")
    else:
        print("All parameters within expected bounds!")

    print("\n" + "="*60)
    print("PARAMETER STATISTICS")
    print("="*60)

    for param, stats in validation_results['parameter_statistics'].items():
        print(f"\n{param.upper()}:")
        print(f"  Count: {stats['count']}")
        print(f"  Mean ± Std: {stats['mean']:.6f} ± {stats['std']:.6f}")
        print(f"  Range: [{stats['min']:.6f}, {stats['max']:.6f}]")
        print(f"  Median: {stats['median']:.6f}")

    # Quality analysis
    print("\n" + "="*60)
    print("PEAK FITTING QUALITY ANALYSIS")
    print("="*60)

    quality_analysis = analyze_peak_quality(data_computed, metadata['measurement_cols'])

    for peak_name, peak_stats in quality_analysis['peak_statistics'].items():
        print(f"\n{peak_name.upper()}:")
        for param, stats in peak_stats.items():
            if stats['coverage_percentage'] > 0:
                print(f"  {param}: {stats['coverage_percentage']:.1f}% coverage ({stats['non_zero_count']}/{stats['total_possible']})")

    if non_zero_count > 0:
        non_zero_values = data_computed[data_computed != 0]

        # Check each measurement dimension
        print("\n" + "="*60)
        print("MEASUREMENT BREAKDOWN")
        print("="*60)
        for i, col_name in enumerate(metadata['measurement_cols']):
            measurement_data = data_computed[:, :, :, i]
            nz_count = np.count_nonzero(measurement_data)
            if nz_count > 0:
                print(f"\n{col_name}:")
                print(f"  Non-zero values: {nz_count}")
                print(f"  Range: [{np.min(measurement_data[measurement_data != 0]):.6f}, {np.max(measurement_data[measurement_data != 0]):.6f}]")

                # Check for suspicious values
                if col_name == 'area' and np.any(measurement_data < 0):
                    print(f"  WARNING: Negative areas detected!")
                if col_name in ['sigma', 'gamma'] and np.any(measurement_data <= 0):
                    print(f"  WARNING: Non-positive {col_name} values detected!")

        # Check specific peaks
        print("\n" + "="*60)
        print("PEAK-WISE ANALYSIS")
        print("="*60)
        for peak_idx in range(data.shape[0]):
            peak_data = data_computed[peak_idx]
            nz_count = np.count_nonzero(peak_data)
            if nz_count > 0:
                miller = metadata.get('peak_miller_indices', [None] * data.shape[0])[peak_idx]
                print(f"\nPeak {peak_idx} (Miller {miller}):")
                print(f"  Total non-zero values: {nz_count}")

                # Check coverage per measurement
                for i, col in enumerate(metadata['measurement_cols']):
                    col_data = peak_data[:, :, i]
                    col_nz = np.count_nonzero(col_data)
                    total_slots = peak_data.shape[0] * peak_data.shape[1]
                    coverage = 100 * col_nz / total_slots if total_slots > 0 else 0
                    if col_nz > 0:
                        print(f"    {col}: {coverage:.1f}% ({col_nz}/{total_slots})")
    else:
        print("\nNo non-zero values found!")
        print("Checking for NaN values...")
        nan_count = np.count_nonzero(np.isnan(data_computed))
        print(f"NaN values: {nan_count}")

    # Create validation report
    if save_validation_report:
        report_path = f"{path}_validation_report.json"
        full_report = {
            'metadata': metadata,
            'compression_analysis': compression_results,
            'validation_results': validation_results,
            'quality_analysis': quality_analysis,
            'data_summary': {
                'total_elements': int(data_computed.size),
                'non_zero_elements': int(non_zero_count),
                'coverage_percentage': float(100 * non_zero_count / data_computed.size),
                'shape': data.shape
            }
        }

        with open(report_path, 'w') as f:
            json.dump(full_report, f, indent=2)
        print(f"\n📊 Validation report saved to: {report_path}")

    # Create plots
    if create_plots and non_zero_count > 0:
        plot_path = path.replace('/', '_').replace('\\', '_')
        plot_parameter_distributions(data_computed, metadata['measurement_cols'], plot_path)
    
    # Check frame numbers and azimuth angles
    frame_nums = da.from_zarr(f"{path}/frame_numbers.zarr")
    az_angles = da.from_zarr(f"{path}/azimuth_angles.zarr")
    
    frame_nums_computed = frame_nums.compute()
    az_angles_computed = az_angles.compute()
    
    print("\nFrame numbers array:")
    print(f"Shape: {frame_nums.shape}")
    print(f"Non-zero elements: {np.count_nonzero(frame_nums_computed)}")
    if np.count_nonzero(frame_nums_computed) > 0:
        print(f"Range: [{np.min(frame_nums_computed[frame_nums_computed != 0])}, {np.max(frame_nums_computed)}]")
        print(f"Sample: {frame_nums_computed[0, :10]}")  # First 10 frames of first peak
    
    print("\nAzimuth angles array:")
    print(f"Shape: {az_angles.shape}")
    print(f"Non-zero elements: {np.count_nonzero(az_angles_computed)}")
    if np.count_nonzero(az_angles_computed) > 0:
        print(f"Range: [{np.min(az_angles_computed[az_angles_computed != 0]):.2f}, {np.max(az_angles_computed):.2f}]")
        print(f"Sample: {az_angles_computed[0, :10]}")  # First 10 azimuths of first peak

    # Diagnostic: Check a specific slice to see the data structure
    print("\n=== Diagnostic: First frame of first peak ===")
    first_frame = data_computed[0, 0, :, :]  # First peak, first frame, all azimuths, all measurements
    print(f"Shape of slice: {first_frame.shape}")
    non_zero_in_frame = np.count_nonzero(first_frame)
    print(f"Non-zero values in this frame: {non_zero_in_frame}")
    if non_zero_in_frame > 0:
        for i, col in enumerate(metadata['measurement_cols']):
            col_data = first_frame[:, i]
            if np.any(col_data != 0):
                print(f"  {col}: {np.count_nonzero(col_data)} non-zero values")

def quick_validation_summary(path: str):
    """Quick validation summary without loading full dataset"""
    try:
        with open(f"{path}/metadata.json", 'r') as f:
            metadata = json.load(f)

        data = da.from_zarr(f"{path}/data.zarr")

        print(f"\nQUICK VALIDATION SUMMARY for {os.path.basename(path)}")
        print("="*60)
        print(f"Dataset shape: {data.shape}")
        print(f"Measurements: {', '.join(metadata['measurement_cols'])}")
        print(f"Expected elements: {data.size:,}")

        # Sample a small portion for quick check
        sample_data = data[:, :10, :10, :].compute()  # First 10 frames, 10 azimuths
        sample_nz = np.count_nonzero(sample_data)
        sample_total = sample_data.size

        print(f"Sample coverage: {100*sample_nz/sample_total:.1f}% ({sample_nz}/{sample_total})")

        if sample_nz > 0:
            print("Data appears to be present")
            return True
        else:
            print("No data found in sample - full analysis recommended")
            return False

    except Exception as e:
        print(f"Error accessing dataset: {e}")
        return False

if __name__ == "__main__":
    import sys

    # Default path
    default_path = "G:/Data/Feb2025/pilatus/A/Zarr/SpeedTall019-A2-CONT-5-1"

    if len(sys.argv) > 1:
        zarr_path = sys.argv[1]
        mode = sys.argv[2] if len(sys.argv) > 2 else "full"
    else:
        zarr_path = default_path
        mode = "full"

    print(f"Zarr Data Inspector")
    print(f"Path: {zarr_path}")
    print(f"Mode: {mode}")

    if mode == "quick":
        quick_validation_summary(zarr_path)
    else:
        # Full inspection with plots and validation
        inspect_zarr_data(zarr_path, create_plots=True, save_validation_report=True)

    print("\n" + "="*60)
    print("USAGE:")
    print("  python check_zarr.py [path] [mode]")
    print("  path: Path to zarr dataset (optional)")
    print("  mode: 'quick' or 'full' (default: full)")
    print("="*60)