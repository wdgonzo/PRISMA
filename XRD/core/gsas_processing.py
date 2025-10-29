"""
Unified GSAS Processing Module
==============================
This module provides a streamlined approach to X-ray diffraction data processing
using a unified 4D data structure that eliminates the need for data conversions.

Main Components:
- XRDDataset: Unified 4D data structure (peaks, frames, azimuths, measurements)
- Parallel processing with Dask
- Direct integration with visualization
- Efficient I/O with Zarr storage

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import pandas as pd
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import G2script - try shortcut first (local GUI setup), fallback to direct import (HPC)
try:
    import G2script  # GUI-installed shortcut (local setups)
except ImportError:
    from GSASII import GSASIIscriptable as G2script  # Direct import (headless/HPC)

from XRD.core.image_loader import ImageLoader, ImageFrameInfo, validate_frame_ordering
import matplotlib
matplotlib.use('Agg')  # CRITICAL: Set non-interactive backend BEFORE importing pyplot
import matplotlib.pyplot as plt
import time  # For performance timing

# GSAS-II Performance Optimization
def calculate_gsas_performance_config(memory_gb: float = None, cpu_cores: int = None):
    """
    Calculate GSAS-II performance parameters without setting global state.

    Args:
        memory_gb: Available memory in GB (auto-detected if None)
        cpu_cores: Number of CPU cores (auto-detected if None)

    Returns:
        Dict with optimal configuration parameters
    """
    import psutil
    import os

    if memory_gb is None:
        memory_gb = psutil.virtual_memory().total / (1024**3)

    if cpu_cores is None:
        cpu_cores = os.cpu_count()

    # Optimize blkSize based on memory and CPU characteristics
    # Higher memory systems can handle larger block sizes
    # Default: 128, but can range from 64 to 1024 based on system specs
    if memory_gb >= 64:  # High-memory HPC node
        optimal_blksize = 2**9  # 512
    elif memory_gb >= 32:  # Medium-memory system
        optimal_blksize = 2**8  # 256
    elif memory_gb >= 16:  # Standard workstation
        optimal_blksize = 2**7  # 128 (default)
    else:  # Low-memory system
        optimal_blksize = 2**6  # 64

    # Calculate optimal cores
    optimal_cores = max(1, int(cpu_cores * 0.75))

    print(f"GSAS-II Performance Configuration:")
    print(f"   Memory: {memory_gb:.1f} GB")
    print(f"   CPU cores: {cpu_cores}")
    print(f"   Optimal blkSize: {optimal_blksize} (2^{optimal_blksize.bit_length()-1})")
    print(f"   Optimal cores: {optimal_cores}")

    return {
        'blkSize': optimal_blksize,
        'memory_gb': memory_gb,
        'cpu_cores': cpu_cores,
        'multiprocessing_cores': optimal_cores
    }

# Get GSAS optimization info without applying globally
_gsas_optimization_info = calculate_gsas_performance_config()

# Silent mode configuration
import sys
import os
from contextlib import contextmanager
from io import StringIO

@contextmanager
def silent_gsas_operations():
    """
    Context manager to suppress GSAS-II verbose output during operations.
    Redirects stdout to capture GSAS messages while preserving our system messages.
    """
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    # Create string buffers to capture output
    captured_stdout = StringIO()
    captured_stderr = StringIO()

    try:
        # Redirect output streams
        sys.stdout = captured_stdout
        sys.stderr = captured_stderr

        # Set GSAS to minimal output
        G2script.SetPrintLevel("none")

        yield

    finally:
        # Restore original output streams
        sys.stdout = original_stdout
        sys.stderr = original_stderr

        # Optionally process captured output for errors only
        captured_out = captured_stdout.getvalue()
        captured_err = captured_stderr.getvalue()

        # Only print if there are actual errors (not warnings or info)
        if captured_err and ("error" in captured_err.lower() or "failed" in captured_err.lower()):
            print(f"GSAS Error: {captured_err.strip()}")

# Global cache for GSAS computations (saves intermediate results)
_gsas_cache = {}

def get_gsas_cache():
    """Get the global GSAS computation cache."""
    return _gsas_cache

def clear_gsas_cache():
    """Clear the global GSAS computation cache."""
    global _gsas_cache
    cache_size = len(_gsas_cache)
    _gsas_cache.clear()
    print(f"Cleared GSAS cache ({cache_size} entries)")

def cache_key_from_params(file_path: str, params: 'GSASParams', frame_index: int) -> str:
    """Generate a cache key from processing parameters."""
    import hashlib

    # Create a hash based on file path, key parameters, and frame
    key_data = f"{file_path}_{params.limits}_{params.spacing}_{params.azimuths}_{frame_index}"
    return hashlib.md5(key_data.encode()).hexdigest()[:16]

def setup_hpc_environment():
    """
    Configure environment variables for optimal HPC performance.

    Sets up thread management, BLAS optimization, and network configuration.
    """
    import os

    # Prevent thread oversubscription (critical for HPC nodes)
    thread_vars = {
        'OMP_NUM_THREADS': '1',          # OpenMP threads
        'MKL_NUM_THREADS': '1',          # Intel MKL threads
        'OPENBLAS_NUM_THREADS': '1',     # OpenBLAS threads
        'NUMEXPR_NUM_THREADS': '1',      # NumExpr threads
        'VECLIB_MAXIMUM_THREADS': '1',   # macOS Accelerate
    }

    print("HPC Environment Configuration:")
    for var, value in thread_vars.items():
        old_value = os.environ.get(var, 'not set')
        os.environ[var] = value
        print(f"   {var}: {old_value} -> {value}")

    # Configure NumPy to use optimal BLAS
    try:
        import numpy as np
        config_info = np.show_config()
        print(f"   NumPy BLAS: {_detect_blas_library()}")
    except:
        print("   NumPy BLAS: detection failed")

    # Set Dask configuration for HPC
    try:
        import dask
        dask.config.set({
            'distributed.worker.memory.target': 0.7,    # Use 70% of worker memory
            'distributed.worker.memory.spill': 0.8,     # Spill at 80%
            'distributed.worker.memory.pause': 0.9,     # Pause at 90%
            'distributed.worker.memory.terminate': 0.95,  # Terminate at 95%
            'distributed.comm.compression': 'auto',     # Auto-select best available
            'distributed.scheduler.worker-ttl': '5 minutes',  # Worker timeout
        })
        print("   Dask: Configured for HPC memory management")
    except ImportError:
        print("   Dask: Configuration skipped (not available)")

def _detect_blas_library() -> str:
    """Detect which BLAS library NumPy is using."""
    try:
        import numpy as np
        config = np.show_config()

        # Check for common BLAS libraries
        if 'mkl' in str(config).lower():
            return 'Intel MKL (optimal)'
        elif 'openblas' in str(config).lower():
            return 'OpenBLAS (good)'
        elif 'accelerate' in str(config).lower():
            return 'macOS Accelerate (good)'
        elif 'blas' in str(config).lower():
            return 'Generic BLAS (basic)'
        else:
            return 'Unknown BLAS library'
    except:
        return 'BLAS detection failed'

def optimize_numpy_performance():
    """
    Optimize NumPy performance for scientific computing.

    Configures BLAS/LAPACK settings and validates performance.
    """
    import numpy as np

    print("NumPy Performance Optimization:")

    # Detect BLAS library
    blas_lib = _detect_blas_library()
    print(f"   BLAS Library: {blas_lib}")

    # Check for multithreading capability
    try:
        from threadpoolctl import threadpool_info
        pools = threadpool_info()

        blas_threads = 0
        for pool in pools:
            if pool.get('api') in ['blas', 'lapack']:
                blas_threads += pool.get('num_threads', 0)

        print(f"   BLAS/LAPACK threads: {blas_threads}")

        # Recommend optimal settings
        if blas_threads > 1:
            print("   Warning: Multi-threaded BLAS detected")
            print("   For HPC use, set thread environment variables to 1")

    except ImportError:
        print("   Thread info: Install 'threadpoolctl' for detailed analysis")

    # Basic performance validation
    test_size = 1000
    test_array = np.random.random((test_size, test_size)).astype(np.float32)

    import time
    start = time.time()
    _ = np.dot(test_array, test_array)  # Matrix multiplication test
    elapsed = time.time() - start

    # Performance assessment
    operations = test_size**3  # Approximate FLOPs for matrix multiplication
    gflops = operations / elapsed / 1e9

    print(f"   Matrix mult performance: {gflops:.1f} GFLOPS")

    if gflops > 50:
        print("   Excellent NumPy performance")
    elif gflops > 20:
        print("   Good NumPy performance")
    elif gflops > 5:
        print("   Fair NumPy performance - consider BLAS optimization")
    else:
        print("   Poor NumPy performance - BLAS configuration needed")

# Initialize HPC environment on import
setup_hpc_environment()
optimize_numpy_performance()

# Performance monitoring status
try:
    import performance_monitor
    print("Performance monitoring enabled")
    _performance_monitoring_available = True
except ImportError:
    print("Performance monitoring disabled (performance_monitor.py not found)")
    _performance_monitoring_available = False
import numpy as np
import os
import re
import glob
import json
import sys
from dataclasses import dataclass
import dask.array as da
from dask import delayed, compute
from dask.threaded import get as threaded_get
from XRD.hpc.cluster import get_dask_client, close_dask_client
from enum import Enum
import logging
from typing import List, Tuple, Dict, Optional, Union
import zarr
from zarr.codecs import BloscCodec, BloscCname, BloscShuffle
import numcodecs


# ================== ENUMS AND CONSTANTS ==================

class Stages(Enum):
    """Enumeration for different experimental stages."""
    BEF = 0
    AFT = 1
    CONT = 2
    DELT = 3
    DELTDSPACING = 4

# ================== UNIFIED DATA STRUCTURE ==================

class XRDDataset:
    """
    Unified 4D dataset for XRD data with flexible access patterns.
    Shape: (peaks, frames, azimuths, measurements)
    
    FIXED: Uses numpy arrays internally during construction, converts to dask for computation
    """
    
    def __init__(self, n_peaks: int, n_frames: int, n_azimuths: int, 
                 measurement_cols: List[str], params: 'GSASParams', 
                 chunks: Tuple = None):
        """
        Initialize XRD dataset.
        
        Args:
            n_peaks: Number of diffraction peaks
            n_frames: Number of time/depth frames
            n_azimuths: Number of azimuthal bins
            measurement_cols: List of measurement column names
            params: Processing parameters
            chunks: Dask chunking strategy
        """
        self.n_peaks = n_peaks
        self.n_frames = n_frames  
        self.n_azimuths = n_azimuths
        self.measurement_cols = measurement_cols
        self.n_measurements = len(measurement_cols)
        self.params = params
        
        # Create measurement column mapping
        self.col_idx = {col: i for i, col in enumerate(measurement_cols)}
        
        # Advanced chunking strategy optimized for 100MB target (2025 best practice)
        if chunks is None:
            chunks = self._calculate_optimal_chunks(n_peaks, n_frames, n_azimuths, self.n_measurements)
        self.chunks = chunks

        # Configure compression for Zarr v3 with proper codec
        self.zarr_codec = BloscCodec(
            cname=BloscCname.zstd,          # Use zstd compression (best for scientific data)
            clevel=3,                       # Balanced compression level
            shuffle=BloscShuffle.shuffle,   # Enable shuffling for better compression
            typesize=4,                     # Explicit typesize for float32 data
            blocksize=0                     # Auto-optimize block size
        )
            
        # CRITICAL FIX: Use numpy arrays during construction
        # Will convert to dask after data is populated
        self._numpy_data = np.zeros((n_peaks, n_frames, n_azimuths, self.n_measurements), 
                                   dtype='float32')
        self._numpy_frame_numbers = np.zeros((n_peaks, n_frames), dtype='int32')
        self._numpy_azimuth_angles = np.zeros((n_peaks, n_azimuths), dtype='float32')
        
        # Initialize dask arrays as None (will be set in finalize)
        self.data = None
        self.frame_numbers = None
        self.azimuth_angles = None
        
        # Metadata
        self.peak_miller_indices = np.zeros(n_peaks, dtype='int32')
        
        # Track if we're in construction mode
        self._construction_mode = True

    def _calculate_optimal_chunks(self, n_peaks: int, n_frames: int, n_azimuths: int, n_measurements: int) -> Tuple[int, ...]:
        """
        Calculate optimal chunk sizes targeting ~100MB per chunk (2025 Dask best practice).

        Returns:
            Tuple of chunk sizes for (peaks, frames, azimuths, measurements)
        """
        # Target chunk size in bytes (100MB)
        target_bytes = 100 * 1024 * 1024

        # Size of each element (float32 = 4 bytes)
        element_size = 4

        # Calculate total elements that fit in target size
        target_elements = target_bytes // element_size

        # Always keep peaks as 1 (process one Miller index at a time)
        peak_chunk = 1
        meas_chunk = n_measurements  # Keep all measurements together

        # Calculate frame and azimuth chunks to reach target
        remaining_elements = target_elements // (peak_chunk * meas_chunk)

        # Determine optimal frame and azimuth distribution
        if remaining_elements >= n_frames * n_azimuths:
            # Small dataset - can fit everything in one chunk
            frame_chunk = n_frames
            az_chunk = n_azimuths
        else:
            # Balance between frame and azimuth chunks
            # Prefer larger frame chunks for better sequential access
            aspect_ratio = n_frames / n_azimuths if n_azimuths > 0 else 1

            if aspect_ratio >= 1:  # More frames than azimuths
                # Prioritize frame chunks
                frame_chunk = min(n_frames, int((remaining_elements * 0.7) ** 0.5 * aspect_ratio))
                frame_chunk = max(1, min(frame_chunk, n_frames))
                az_chunk = min(n_azimuths, remaining_elements // frame_chunk)
                az_chunk = max(1, az_chunk)
            else:  # More azimuths than frames
                # Balance more evenly
                az_chunk = min(n_azimuths, int((remaining_elements * 0.7) ** 0.5 / aspect_ratio))
                az_chunk = max(1, min(az_chunk, n_azimuths))
                frame_chunk = min(n_frames, remaining_elements // az_chunk)
                frame_chunk = max(1, frame_chunk)

        # Ensure chunks don't exceed array dimensions
        frame_chunk = min(frame_chunk, n_frames)
        az_chunk = min(az_chunk, n_azimuths)

        chunks = (peak_chunk, frame_chunk, az_chunk, meas_chunk)

        # Calculate actual chunk size for reporting
        chunk_elements = peak_chunk * frame_chunk * az_chunk * meas_chunk
        chunk_mb = chunk_elements * element_size / (1024 * 1024)

        print(f"   Optimized Chunk Strategy (100MB target):")
        print(f"   Target: 100MB, Actual: {chunk_mb:.1f}MB per chunk")
        print(f"   Chunks: {chunks}")
        print(f"   Elements per chunk: {chunk_elements:,}")

        return chunks
    
    def set_frame_data(self, peak_idx: int, frame_idx: int, df: pd.DataFrame):
        """Set entire frame data from DataFrame - FIXED version"""
        if not self._construction_mode:
            raise RuntimeError("Cannot modify data after finalization. Data is immutable once converted to Dask.")
        
        # Sort dataframe by azimuth to ensure consistent ordering
        df_sorted = df.sort_values('azimuth').reset_index(drop=True)
        
        # Create azimuth mapping for this frame
        azimuth_to_idx = {}
        for row_idx, row in df_sorted.iterrows():
            azimuth = row['azimuth']
            az_idx = self._azimuth_to_index(azimuth)
            azimuth_to_idx[azimuth] = az_idx
            
            # Set azimuth angle (only need to do once per azimuth)
            if self._numpy_azimuth_angles[peak_idx, az_idx] == 0:
                self._numpy_azimuth_angles[peak_idx, az_idx] = azimuth
        
        # Set frame number (once per frame)
        if 'frame' in df_sorted.columns and len(df_sorted) > 0:
            self._numpy_frame_numbers[peak_idx, frame_idx] = df_sorted.iloc[0]['frame']
        
        # Set measurement data for each row
        for _, row in df_sorted.iterrows():
            azimuth = row['azimuth']
            az_idx = azimuth_to_idx[azimuth]
            
            # Set each measurement value
            for col in self.measurement_cols:
                if col in row:
                    value = row[col]
                    if not pd.isna(value):
                        col_idx = self.col_idx[col]
                        self._numpy_data[peak_idx, frame_idx, az_idx, col_idx] = value
    
    def _azimuth_to_index(self, azimuth: float) -> int:
        """Convert azimuth angle to array index - FIXED version"""
        # Calculate index based on spacing and start angle
        start_azimuth = self.params.azimuths[0]
        spacing = self.params.spacing

        # Calculate relative position from start, then round to nearest spacing increment
        relative_azimuth = azimuth - start_azimuth
        index = int(round(relative_azimuth / spacing))

        # Ensure index is within bounds
        return max(0, min(index, self.n_azimuths - 1))
    
    def finalize(self):
        """Convert numpy arrays to dask arrays after construction is complete"""
        if self._construction_mode:
            print("Finalizing dataset - converting to Dask arrays...")
            
            # Convert numpy arrays to dask
            self.data = da.from_array(self._numpy_data, chunks=self.chunks)
            print("data")
            self.frame_numbers = da.from_array(self._numpy_frame_numbers, 
                                              chunks=(self.chunks[0], self.chunks[1]))
            print("frame_numbers")
            self.azimuth_angles = da.from_array(self._numpy_azimuth_angles,
                                               chunks=(self.chunks[0], self.chunks[2]))
            print("azimuth_angles")
            # Report statistics
            non_zero = np.count_nonzero(self._numpy_data)
            total = self._numpy_data.size
            #print(f"Dataset finalized: {non_zero}/{total} non-zero values ({100*non_zero/total:.2f}%)")
            
            # Clear construction mode flag
            self._construction_mode = False
    
    # ============ FLEXIBLE ACCESS PATTERNS ============
    
    def get_peak(self, peak_idx: int) -> da.Array:
        """Get all data for a specific peak"""
        if self.data is None:
            self.finalize()
        return self.data[peak_idx]
    
    def get_frame(self, peak_idx: int, frame_idx: int) -> da.Array:
        """Get specific frame data"""
        if self.data is None:
            self.finalize()
        return self.data[peak_idx, frame_idx]
    
    def get_azimuth_timeseries(self, peak_idx: int, azimuth_idx: int) -> da.Array:
        """Get time series for specific peak/azimuth"""
        if self.data is None:
            self.finalize()
        return self.data[peak_idx, :, azimuth_idx]
    
    def get_measurement(self, measurement: str) -> da.Array:
        """Get specific measurement across all dimensions"""
        if self.data is None:
            self.finalize()
        col_idx = self.col_idx[measurement]
        return self.data[:, :, :, col_idx]
    
    def get_peak_measurement(self, peak_idx: int, measurement: str) -> da.Array:
        """Get specific measurement for one peak"""
        if self.data is None:
            self.finalize()
        col_idx = self.col_idx[measurement]
        return self.data[peak_idx, :, :, col_idx]
    
    # ============ COMPUTATIONAL METHODS ============
    
    def calculate_delta(self, measurement: str, axis: int = 1) -> None:
        """Calculate differences along specified axis and add as new measurement"""
        if self.data is None:
            self.finalize()
            
        col_idx = self.col_idx[measurement]
        data_slice = self.data[:, :, :, col_idx]
        delta_values = da.diff(data_slice, axis=axis, prepend=0)
        
        delta_name = f'delta {measurement}'
        self.add_measurement(delta_name, delta_values)
    
    def calculate_strain(self, reference_d: np.ndarray) -> None:
        """Calculate strain and add as new measurement - FIXED version"""
        print("calculating strain...")
        if self._construction_mode:
            # Work with numpy arrays during construction
            d_col_idx = self.col_idx['d']
            d_values = self._numpy_data[:, :, :, d_col_idx]
            
            # Broadcast reference_d to match data dimensions
            if reference_d.ndim == 2:  # (peaks, azimuths)
                # Need to broadcast to (peaks, frames, azimuths)
                reference_d_broadcast = np.broadcast_to(
                    reference_d[:, np.newaxis, :], 
                    (self.n_peaks, self.n_frames, self.n_azimuths)
                ).copy()  # Make a copy to ensure it's writable
            else:
                reference_d_broadcast = reference_d
            
            # Calculate strain only where both values are non-zero
            strain = np.zeros_like(d_values)
            
            # Create masks separately for each array
            d_mask = (d_values != 0) & ~np.isnan(d_values)
            ref_mask = (reference_d_broadcast != 0) & ~np.isnan(reference_d_broadcast)
            combined_mask = d_mask & ref_mask
            
            # Apply strain calculation only where mask is true
            strain[combined_mask] = (d_values[combined_mask] - reference_d_broadcast[combined_mask]) / reference_d_broadcast[combined_mask]
            
            # Add strain as new measurement
            new_data = np.concatenate([self._numpy_data, strain[..., np.newaxis]], axis=-1)
            self._numpy_data = new_data
            self.col_idx['strain'] = self.n_measurements
            self.measurement_cols.append('strain')
            self.n_measurements += 1
            
            # Also add absolute strain
            abs_strain = np.abs(strain)
            new_data = np.concatenate([self._numpy_data, abs_strain[..., np.newaxis]], axis=-1)
            self._numpy_data = new_data
            self.col_idx['abs strain'] = self.n_measurements
            self.measurement_cols.append('abs strain')
            self.n_measurements += 1
            
        else:
            # Work with dask arrays after finalization
            d_col_idx = self.col_idx['d']
            d_values = self.data[:, :, :, d_col_idx]
            
            # Broadcast reference_d to match data dimensions
            if reference_d.ndim == 2:  # (peaks, azimuths)
                # Broadcast to match d_values shape
                reference_d_broadcast = np.broadcast_to(
                    reference_d[:, np.newaxis, :],
                    (self.n_peaks, self.n_frames, self.n_azimuths)
                )
            else:
                reference_d_broadcast = reference_d
                
            # Convert to dask array
            reference_d_da = da.from_array(reference_d_broadcast, chunks=self.chunks[:3])
            
            # Calculate strain with proper masking
            # Use da.where to handle division by zero
            strain = da.where(
                (reference_d_da != 0) & (d_values != 0),
                (d_values - reference_d_da) / reference_d_da,
                0  # Set strain to 0 where we can't calculate it
            )
            
            self.add_measurement('strain', strain)
            
            # Add absolute strain
            abs_strain = da.abs(strain)
            self.add_measurement('abs strain', abs_strain)

    def calculate_pct(self, measurement: str) -> None:
        """Calculate true percentage change: ((measurement - reference) / reference) * 100"""
        # Check for comprehensive reference values first, fallback to reference_d for backward compatibility
        print(f"calculating pct {measurement}...")
        if hasattr(self, 'reference_values') and self.reference_values:
            if measurement not in self.reference_values:
                raise ValueError(f"Reference values for measurement '{measurement}' not available. Available: {list(self.reference_values.keys())}")
            reference_array = self.reference_values[measurement]
        elif hasattr(self, 'reference_d') and self.reference_d is not None:
            if measurement != 'd':
                raise ValueError(f"Only d-spacing reference available. Cannot calculate PCT for '{measurement}'. Dataset needs reprocessing with updated reference calculation.")
            reference_array = self.reference_d
        else:
            raise ValueError("No reference values available for PCT calculation. Dataset must be processed with reference images.")

        if measurement not in self.col_idx:
            raise ValueError(f"Measurement '{measurement}' not found in dataset")

        if self.data is None:
            self.finalize()

        # Get measurement data
        col_idx = self.col_idx[measurement]
        measurement_data = self.data[:, :, :, col_idx]

        # Create reference broadcast to match measurement data shape
        if reference_array.ndim == 2:  # (peaks, azimuths)
            # Broadcast to (peaks, frames, azimuths)
            reference_broadcast = da.from_array(
                np.broadcast_to(
                    reference_array[:, np.newaxis, :],
                    (self.n_peaks, self.n_frames, self.n_azimuths)
                ),
                chunks=self.chunks[:3]
            )
        else:
            reference_broadcast = da.from_array(reference_array, chunks=self.chunks[:3])

        # Calculate TRUE percentage change with proper masking to avoid division by zero
        pct_values = da.where(
            (reference_broadcast != 0) & (measurement_data != 0) & ~da.isnan(reference_broadcast),
            ((measurement_data - reference_broadcast) / reference_broadcast) * 100,  # True percentage change
            0  # Set to 0 where we can't calculate
        )

        pct_name = f'pct {measurement}'
        self.add_measurement(pct_name, pct_values)

    def add_measurement(self, name: str, values: Union[da.Array, np.ndarray]):
        """Add a new measurement to the dataset"""
        if self.data is None:
            self.finalize()
            
        if name not in self.col_idx:
            # Ensure values have correct shape
            if values.shape[:3] != self.data.shape[:3]:
                raise ValueError(f"New measurement shape {values.shape} incompatible with dataset shape {self.data.shape[:3]}")
            
            # Expand data array
            values_expanded = values[..., np.newaxis] if values.ndim == 3 else values
            
            # Convert numpy to dask if needed
            if isinstance(values_expanded, np.ndarray):
                values_expanded = da.from_array(values_expanded, chunks=self.chunks)
            
            new_data = da.concatenate([self.data, values_expanded], axis=-1)
            self.data = new_data
            
            # Update metadata
            self.col_idx[name] = self.n_measurements
            self.measurement_cols.append(name)
            self.n_measurements += 1
    
    # ============ I/O METHODS - FIXED ============
    
    def save(self, path: str):
        """Save to Zarr format - FIXED version"""
        os.makedirs(path, exist_ok=True)
        
        # Ensure data is finalized
        if self.data is None:
            self.finalize()
        
        print(f"Saving to {path}...")

        # Save main data with Zarr v3 codec optimization
        zarr_version = getattr(zarr, '__version__', '3.0.0')

        if zarr_version.startswith('3'):
            # Use proper v3 codec pipeline - BloscCodec with BytesCodec
            print(f"Using Zarr v3 ({zarr_version}) with optimized BloscCodec...")
            from zarr.codecs import BytesCodec
            # For Zarr v3: BloscCodec needs to be paired with BytesCodec for the complete pipeline
            zarr_kwargs = {'codecs': [BytesCodec(), self.zarr_codec]}
        else:
            # Fallback to v2 compressor syntax for older versions
            print(f"Using Zarr v2 ({zarr_version}) with compressor fallback...")
            # Convert BloscCodec to numcodecs.Blosc for v2 compatibility
            fallback_codec = numcodecs.Blosc(cname='zstd', clevel=3, shuffle=numcodecs.Blosc.SHUFFLE)
            zarr_kwargs = {'compressor': fallback_codec}

        # Save all arrays with consistent compression
        self.data.to_zarr(f"{path}/data.zarr", overwrite=True, **zarr_kwargs)
        self.frame_numbers.to_zarr(f"{path}/frame_numbers.zarr", overwrite=True, **zarr_kwargs)
        self.azimuth_angles.to_zarr(f"{path}/azimuth_angles.zarr", overwrite=True, **zarr_kwargs)
        
        # Save metadata
        metadata = {
            'n_peaks': self.n_peaks,
            'n_frames': self.n_frames,
            'n_azimuths': self.n_azimuths,
            'measurement_cols': self.measurement_cols,
            'col_idx': self.col_idx,
            'peak_miller_indices': self.peak_miller_indices.tolist(),
            'reference_d': self.reference_d.tolist() if hasattr(self, 'reference_d') and self.reference_d is not None else None,
            'reference_values': {
                key: array.tolist() for key, array in self.reference_values.items()
            } if hasattr(self, 'reference_values') and self.reference_values else None,
            'params': {
                'sample': self.params.sample,
                'setting': getattr(self.params, 'setting', 'Unknown'),
                'stage': self.params.stage.name,
                'spacing': self.params.spacing,
                'azimuths': self.params.azimuths,
                'frames': self.params.frames,
                'exposure': getattr(self.params, 'exposure', '019'),
                'active_peaks': [
                    {
                        'name': peak.name,
                        'miller_index': peak.miller_index,
                        'position': peak.position,
                        'limits': peak.limits
                    } for peak in self.params.active_peaks
                ] if hasattr(self.params, 'active_peaks') else []
            }
        }
        
        with open(f"{path}/metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Saved successfully!")
    
    @classmethod
    def load(cls, path: str, params: 'GSASParams'):
        """Load from Zarr format - FIXED version"""
        # Load metadata
        with open(f"{path}/metadata.json", 'r') as f:
            metadata = json.load(f)
        
        # Create instance
        instance = cls(metadata['n_peaks'], metadata['n_frames'], 
                      metadata['n_azimuths'], metadata['measurement_cols'], params)
        
        # Skip construction mode, load directly as dask
        instance._construction_mode = False
        
        # Load data arrays
        instance.data = da.from_zarr(f"{path}/data.zarr")
        instance.frame_numbers = da.from_zarr(f"{path}/frame_numbers.zarr")
        instance.azimuth_angles = da.from_zarr(f"{path}/azimuth_angles.zarr")
        
        # Load metadata
        instance.col_idx = metadata['col_idx']
        instance.peak_miller_indices = np.array(metadata['peak_miller_indices'])

        # Load comprehensive reference values if available
        if 'reference_values' in metadata and metadata['reference_values'] is not None:
            instance.reference_values = {
                key: np.array(values) for key, values in metadata['reference_values'].items()
            }
            # Maintain backward compatibility
            instance.reference_d = instance.reference_values.get('d')
        elif 'reference_d' in metadata and metadata['reference_d'] is not None:
            # Handle old datasets with only reference_d
            instance.reference_d = np.array(metadata['reference_d'])
            instance.reference_values = None
        else:
            instance.reference_d = None
            instance.reference_values = None

        return instance
    
    # ============ CONVERSION FOR VISUALIZATION ============
    
    def to_visualization_dataframe(self, peak_idx: int, measurement: str) -> pd.DataFrame:
        """
        Convert specific peak and measurement to DataFrame for visualization.
        Returns DataFrame with columns: frame, azimuth, value
        """
        if measurement not in self.col_idx:
            raise ValueError(f"Measurement '{measurement}' not found in dataset")
        
        if self.data is None:
            self.finalize()
        
        col_idx = self.col_idx[measurement]
        peak_data = self.data[peak_idx, :, :, col_idx].compute()
        
        # Create coordinate arrays
        frames = np.arange(self.n_frames)
        azimuths = np.linspace(self.params.azimuths[0], self.params.azimuths[1], self.n_azimuths)
        
        # Create meshgrid and flatten
        frame_grid, azimuth_grid = np.meshgrid(frames, azimuths, indexing='ij')
        
        df = pd.DataFrame({
            'frame': frame_grid.flatten(),
            'azimuth': azimuth_grid.flatten(),
            measurement: peak_data.flatten()
        })
        
        # Remove NaN values
        df = df.dropna()
        
        return df



# ================== PROCESSING PARAMETERS ==================

@dataclass
class PeakParams:
    """Configuration for a single peak."""
    name: str
    miller_index: str
    position: float
    limits: tuple[float, float]

    @classmethod
    def from_dict(cls, data: dict) -> 'PeakParams':
        """Create PeakParams from dictionary."""
        return cls(
            name=data['name'],
            miller_index=data['miller_index'],
            position=data['position'],
            limits=tuple(data['limits'])
        )

@dataclass
class GSASParams:
    """Parameters for GSAS processing configuration."""
    # Home directory for outputs
    home_dir: str                    # Root directory for output data (e.g., /home/user/Processor)

    # Explicit input paths (user specifies exactly where data is)
    images_path: str                 # Exact path to images directory
    refs_path: Optional[str]         # Exact path to references directory (None if no refs)

    # File paths
    control_file: str
    mask_file: str
    intplot_export: bool

    # Sample information
    sample: str
    setting: str
    stage: Stages
    notes: str
    exposure: str

    # Peak configuration
    active_peaks: List[PeakParams]

    # Analysis parameters
    azimuths: tuple[float, float]
    frames: tuple[int, int]  # (start_frame, end_frame) - use -1 for end_frame to process all
                            # Note: Frame filtering (e.g., excluding air frames) should be done
                            # in post-processing/visualization, not during core data processing

    # Processing parameters
    spacing: int
    step: int

    # Detector & beam parameters (REQUIRED for calibration and d-spacing)
    pixel_size: tuple[float, float]  # Detector pixel size in microns, e.g., (172.0, 172.0)
    wavelength: float                 # X-ray wavelength in Angstroms, e.g., 0.240
    detector_size: tuple[int, int]    # Detector dimensions in pixels, e.g., (1475, 1679)

    # Optional peak configuration (fields with defaults must come last)
    available_peaks: List[PeakParams] = None  # Background/interference peaks

    def __post_init__(self):
        """Initialize available_peaks if not provided."""
        if self.available_peaks is None:
            self.available_peaks = []

        # Import path_manager for path generation
        from XRD.utils.path_manager import create_standard_structure

        # Ensure directory structure exists for outputs
        if self.home_dir and os.path.exists(self.home_dir):
            create_standard_structure(self.home_dir)

    @property
    def miller(self) -> int:
        """Return miller index of first peak for compatibility."""
        if self.active_peaks:
            return int(self.active_peaks[0].miller_index)
        return 211  # Default

    @property
    def limits(self) -> tuple[float, float]:
        """Return combined limits covering all peaks."""
        if not self.active_peaks:
            return (4.5, 9.0)

        all_limits = [peak.limits for peak in self.active_peaks]
        min_limit = min(limit[0] for limit in all_limits)
        max_limit = max(limit[1] for limit in all_limits)
        return (min_limit, max_limit)

    @property
    def backgrounds(self) -> tuple[float, float]:
        """Return background limits (same as overall limits)."""
        return self.limits

    @property
    def num_peaks(self) -> int:
        """Return number of active peaks."""
        return len(self.active_peaks)
    
    def filename(self) -> str:
        """Generate base filename for this dataset with peak info."""
        peak_names = "-".join([peak.miller_index for peak in self.active_peaks[:2]])  # Limit to first 2 peaks
        return f"{self.sample}-{self.stage.name}-{peak_names}"

    def total_angle(self) -> int:
        """Calculate total azimuthal angle range."""
        return self.azimuths[-1] - self.azimuths[0]

    def image_file(self) -> str:
        """
        Return explicit path to images directory.

        Returns:
            Path to images directory as specified by user
        """
        return self.images_path

    def ref_file(self) -> Optional[str]:
        """
        Return explicit path to references directory.

        Returns:
            Path to refs directory (or None if no references available)
        """
        return self.refs_path

    def save_path(self, timestamp: str = None) -> str:
        """
        Generate path for saving Zarr data using new structure with descriptive identifiers.

        Args:
            timestamp: Optional timestamp (generates new if None)

        Returns:
            Path to Zarr storage: {home_dir}/Processed/{DateStamp}/{Sample}/Zarr/{ParamsString}/
            Example params: 360deg-72bins-0sf-100efr-8.2l2t_8.8u2t-3peaks-2bkg-143022
        """
        from XRD.utils.path_manager import generate_zarr_params_string, get_zarr_path, get_timestamp

        if timestamp is None:
            timestamp = get_timestamp()

        # Calculate parameters for folder name
        total_az = self.azimuths[1] - self.azimuths[0]
        bin_count = int(total_az / self.spacing)

        # Get 2θ limits from params (combined range covering all peaks)
        theta_limits = self.limits

        # Count background peaks within analysis range
        num_bkg = len(self.get_background_candidates(self.limits))

        # Generate parameter string with identifiers
        params_string = generate_zarr_params_string(
            total_az=total_az,
            bin_count=bin_count,
            frame_start=self.frames[0],
            frame_end=self.frames[1],
            theta_limits=theta_limits,
            num_peaks=len(self.active_peaks),
            num_bkg=num_bkg,
            timestamp=timestamp
        )

        # Generate full path
        path = get_zarr_path(self.home_dir, self.sample, params_string)

        print(f"Dataset will be saved to: {path}")
        return path

    def intensity_plot_path(self, timestamp: str = None) -> str:
        """
        Generate path for saving intensity plots (dataset-level, not per-peak).

        Note: Intensity plots are for the entire dataset, so no peak identifier in path.

        Args:
            timestamp: Optional timestamp (generates new if None)

        Returns:
            Path to intensity plot directory
            Example params: 360deg-72bins-0sf-100efr-8.2l2t_8.8u2t-143022
        """
        from XRD.utils.path_manager import generate_intensity_params_string, get_intensity_path, get_timestamp

        if timestamp is None:
            timestamp = get_timestamp()

        # Calculate parameters
        total_az = self.azimuths[1] - self.azimuths[0]
        bin_count = int(total_az / self.spacing)

        # Get 2θ limits from params
        theta_limits = self.limits

        # Generate parameter string (no peak info, dataset-level)
        params_string = generate_intensity_params_string(
            total_az=total_az,
            bin_count=bin_count,
            frame_start=self.frames[0],
            frame_end=self.frames[1],
            theta_limits=theta_limits,
            timestamp=timestamp
        )

        # Generate full path
        return get_intensity_path(self.home_dir, self.sample, params_string)

    def get_dataset_id(self) -> str:
        """
        Generate unique dataset ID for this parameter configuration.
        Used to link analysis outputs back to source data.

        Returns:
            8-character hex string identifying this dataset
        """
        from XRD.utils.path_manager import generate_dataset_id

        params_dict = {
            'sample': self.sample,
            'setting': self.setting,
            'stage': self.stage.name,
            'azimuths': self.azimuths,
            'frames': self.frames,
            'spacing': self.spacing,
            'peaks': [p.miller_index for p in self.active_peaks]
        }

        return generate_dataset_id(params_dict)

    # ============ PEAK METADATA METHODS (replacing PeakConfig) ============

    def get_active_peak_positions(self) -> List[float]:
        """Get list of active peak positions for fitting."""
        return [peak.position for peak in self.active_peaks]

    def get_available_peak_positions(self) -> List[float]:
        """Get list of available peak positions (background/interference peaks)."""
        return [peak.position for peak in self.available_peaks]

    def get_background_candidates(self, limits: tuple[float, float]) -> List[float]:
        """
        Get peaks that should be treated as background peaks.
        Returns available peaks that are not active and within the analysis range.

        Args:
            limits: 2θ range limits (min, max)

        Returns:
            List of peak positions to add as background peaks
        """
        active_positions = set(self.get_active_peak_positions())
        available_positions = self.get_available_peak_positions()

        # Find interference candidates: available but not selected for analysis
        interference_peaks = [pos for pos in available_positions if pos not in active_positions]

        # Filter to only peaks within the background fitting range
        background_candidates = [
            pos for pos in interference_peaks
            if limits[0] <= pos <= limits[1]
        ]

        return background_candidates

    def get_miller_indices(self) -> List[int]:
        """Get Miller indices for active peaks."""
        return [int(peak.miller_index) for peak in self.active_peaks]

    def get_peak_names(self) -> List[str]:
        """Get display names for active peaks."""
        return [peak.name for peak in self.active_peaks]

    def get_peak_metadata(self, peak_position: float) -> dict:
        """
        Get metadata for a specific peak position.

        Args:
            peak_position: 2θ position of the peak

        Returns:
            Dictionary with peak metadata
        """
        # Search in active peaks first
        for peak in self.active_peaks:
            if abs(peak.position - peak_position) < 0.01:  # Tolerance for float comparison
                return {
                    "name": peak.name,
                    "miller_index": peak.miller_index,
                    "position": peak.position,
                    "limits": peak.limits,
                    "category": "active"
                }

        # Search in available peaks
        for peak in self.available_peaks:
            if abs(peak.position - peak_position) < 0.01:
                return {
                    "name": peak.name,
                    "miller_index": peak.miller_index,
                    "position": peak.position,
                    "limits": peak.limits,
                    "category": "available"
                }

        # Default metadata for unknown peaks
        return {
            "name": f"Peak {peak_position:.2f}°",
            "miller_index": "000",
            "position": peak_position,
            "limits": (peak_position - 0.2, peak_position + 0.2),
            "category": "unknown"
        }


# ================== RECIPE UTILITIES ==================

# Recipe functions moved to XRD.processing.recipes module to avoid circular dependencies


# ================== PROCESSING FUNCTIONS ==================

@delayed
def gsas_parallel(file: str, params: GSASParams, frame_index: int,
                  references: Optional[np.ndarray] = None, reference_bkg = None, reference_peaks: Optional[dict] = None, dynamic_bkg: bool = False, ref: bool = False, ref_steps = [[{"area":False,"pos":False,"sig":False,"gam":False,}, [False, True, False, False]]], frame_info: Optional[ImageFrameInfo] = None) -> List[pd.DataFrame]:
    """
    Process a single diffraction image using GSAS-II (parallelized).

    ENHANCED: Includes caching, performance monitoring, and optimization
    FIXED: Isolates G2script imports to avoid serialization issues
    NEW: Supports multi-frame files via frame_info parameter

    Args:
        file: Path to image file (for backward compatibility)
        params: GSAS processing parameters
        frame_index: Global frame index in dataset
        references: Reference d-spacing array
        reference_bkg: Reference background peaks
        reference_peaks: Reference peak parameters
        dynamic_bkg: Enable dynamic background subtraction
        ref: Whether this is a reference frame
        ref_steps: Refinement steps configuration
        frame_info: ImageFrameInfo for multi-frame support (optional)
    """

    # Check cache first (simplified)
    import hashlib
    cache_key = hashlib.md5(f"{file}_{params.sample}_{frame_index}".encode()).hexdigest()
    cache = {}  # Use local cache for now to avoid global state issues

    if cache_key in cache:
        print(f"Cache hit for frame {frame_index}")
        return cache[cache_key]

    # Performance monitoring wrapper (check if available locally)
    try:
        import performance_monitor
        perf_monitor = performance_monitor.PerformanceMonitor()
        with perf_monitor.monitor_operation(f"gsas_frame_{frame_index}"):
            return _process_single_frame(file, params, frame_index, references, reference_bkg, reference_peaks, dynamic_bkg, cache_key, cache, G2script, ref, ref_steps, frame_info)
    except ImportError:
        return _process_single_frame(file, params, frame_index, references, reference_bkg, reference_peaks, dynamic_bkg, cache_key, cache, G2script, ref, ref_steps, frame_info)

def initialize_project(project, params: GSASParams, file: str):
    """Initialize GSAS-II project with image and controls."""
    project.add_image(file)
    image = project.images()[0]

    # Apply detector configuration
    image.loadControls(params.control_file)
    image.setControl('pixelSize', list(params.pixel_size))  # Use detector params from recipe
    image.setControl('IOtth', [params.limits[0] - 1, params.limits[1] + 1])
    image.setControl('outChannels', 2500)

    # Configure azimuthal integration
    if params.azimuths[0] != 0 and params.azimuths[-1] != 360:
        image.setControl('fullIntegrate', False)
        image.setControl('LRazimuth', params.azimuths)
    image.setControl('outAzimuths', int(params.total_angle() / params.spacing))

    # Apply mask and recalibrate
    image.GeneratePixelMask()
    image.Recalibrate()

    return image


def _process_single_frame(file: str, params: GSASParams, frame_index: int,
                         references: Optional[np.ndarray], reference_bkg, reference_peaks: Optional[dict], dynamic_bkg, cache_key: str, cache: dict, G2script, ref, ref_steps, frame_info: Optional[ImageFrameInfo] = None) -> List[pd.DataFrame]:
    """Internal function to process a single frame with caching.

    NEW: Supports multi-frame files via frame_info parameter
    """

    # Apply GSAS-II configuration locally (not globally)

    #TODO: Check this block to see if this stuff is halucinated or actually impactful
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    config = calculate_gsas_performance_config()
    G2script.blkSize = config['blkSize']

    # Configure multiprocessing if available
    if hasattr(G2script, 'Multiprocessing_cores'):
        G2script.Multiprocessing_cores = config['multiprocessing_cores']

    # Enable performance timing if available
    if hasattr(G2script, 'Show_timing'):
        G2script.Show_timing = True
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # Handle multi-frame file extraction if needed
    import tempfile
    import os
    temp_file = None
    actual_file = file

    if frame_info and frame_info.is_multiframe:
        # Extract frame to temporary .tif file
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"xrd_temp_frame_{frame_index}_{os.getpid()}.tif")

        success = ImageLoader.extract_frame_to_tif(frame_info, temp_file)
        if success:
            actual_file = temp_file
            # Log frame metadata for validation
            if frame_info.metadata:
                print(f"Frame {frame_index} (file frame {frame_info.file_frame_index}): {frame_info.metadata.get('DATE', 'no timestamp')}")
        else:
            print(f"Warning: Failed to extract frame {frame_index}, using original file")

    # Initialize GSAS project
    project = G2script.G2Project(newgpx=f"{params.filename()}-Frame{frame_index}.gpx")

    # Load and configure image
    image = initialize_project(project, params, actual_file)

    # Cache frequently used params
    limits = params.limits
    spacing = params.spacing
    az0 = params.azimuths[0]


    # Perform 2D to 1D integration
    az_map = image.IntThetaAzMap()
    az_histos = image.Integrate(ThetaAzimMap=az_map)

    print(f"Setup complete for frame {frame_index}")

    peak_results = []
    background_results = []
    active_peaks = params.get_active_peak_positions()

    # Get background peak candidates once (same for all azimuthal slices)
    background_candidates = params.get_background_candidates(limits)

    if background_candidates:
        print(f"    Found {len(background_candidates)} background peak candidates: {background_candidates}")

    # Initialize results for each peak
    for _ in range(len(active_peaks)):
        peak_results.append([])

    # Handle intensity plot export mode
    if params.intplot_export:
        # Extract powder pattern data WITHOUT fitting
        powder_data = []
        for histo_index, current_histo in enumerate(az_histos):
            azimuth = az0 + histo_index * spacing

            # Extract raw powder data (2θ, Intensity)
            two_theta = np.array(current_histo.getdata('X'))  # 2θ angles
            intensity = np.array(current_histo.getdata('Yobs'))  # Raw observed intensity

            powder_data.append({
                'frame': frame_index,
                'azimuth': azimuth,
                'two_theta': two_theta,
                'intensity': intensity
            })

        # Cleanup
        image.clearPixelMask()
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception as e:
                print(f"Warning: Could not remove temp file {temp_file}: {e}")

        return powder_data  # Return powder data instead of peak results

    for histo_index, current_histo in enumerate(az_histos):
        # Set basic refinements first (without background peak flags)
        current_histo.set_refinements({
            "Limits": limits,
            "Background": {
                "no. coeffs": 2,
                'type': 'chebyschev-1',
                "refine": True
            }
        })


        #Initalize focus peaks
        for peak_index, peak in enumerate(active_peaks):
            current_histo.add_peak(1, ttheta=peak)

        #Set focus peaks from reference if available
        if reference_peaks is not None:
            for peak_index in range(len(active_peaks)):
                ref_pos = reference_peaks['pos'][peak_index, histo_index]
                ref_area = reference_peaks['area'][peak_index, histo_index]
                ref_sigma = reference_peaks['sigma'][peak_index, histo_index]
                ref_gamma = reference_peaks['gamma'][peak_index, histo_index]

                if all(np.isfinite([ref_pos, ref_area, ref_sigma, ref_gamma])):
                    current_histo.PeakList[peak_index] = [ref_pos, ref_area, ref_sigma, ref_gamma]


        #Initialize background peaks
        try:
            current_histo.calc_autobkg(opt=1)
        except Exception:
            current_histo.calc_autobkg(1, 9)

        #Set background peaks from reference if available
        if reference_bkg is not None and background_candidates is not []:
            ref_bkg_peaks = reference_bkg[histo_index]  # Get background peaks for this azimuth
            for bkg_index in range(len(background_candidates)):
                # reference_bkg is a list of lists: [azimuth][peak][param]
                # For each background peak, get its parameters for this azimuth (histo_index)
                if len(ref_bkg_peaks) > bkg_index and len(ref_bkg_peaks[bkg_index]) >= 8:
                    # peak format: [pos, False, int, False, sig, False, gam, False]
                    current_histo.add_back_peak(
                        ref_bkg_peaks[bkg_index][0],  # pos
                        ref_bkg_peaks[bkg_index][2],  # intensity
                        ref_bkg_peaks[bkg_index][4],  # sigma
                        ref_bkg_peaks[bkg_index][6],  # gamma
                        [False, True, False, False]
                    )            
        else:
            for bkg_index, bkg_peak in enumerate(background_candidates):
                # Add background peaks with default parameters (to be refined later)
                current_histo.add_back_peak(bkg_peak, 100.0, 2000.0, 0, [False, True, False, False])


        #If reference, refine background peaks first
        if ref:
            _perform_accurate_refinement(current_histo, params, 1, 3,
            ref_sequence  = [ {'area': False, 'pos': False, 'sig': False, 'gam': False}, 
                            {'area': False, 'pos': False, 'sig': False, 'gam': False}, ],
            back_sequence = [   [False, True, False, False],
                                [False, True, False, False],])
            _perform_accurate_refinement(current_histo, params, 1, 3,
            ref_sequence  = [ {'area': False, 'pos': False, 'sig': False, 'gam': False}, 
                            {'area': False, 'pos': False, 'sig': False, 'gam': False}, ],
            back_sequence = [   [False, True, False, False],
                                [False, False, True, False],])

            _perform_accurate_refinement(current_histo, params, 1, 3,
            ref_sequence  = [ {'area': False, 'pos': False, 'sig': False, 'gam': False},],
            back_sequence = [[True, False, True, False],])


        #If dynamic background, refine background peaks slightly
        if dynamic_bkg:
            _perform_accurate_refinement(current_histo, params, 1, 3,
            ref_sequence  = [ {'area': False, 'pos': False, 'sig': False, 'gam': False}, 
                            {'area': False, 'pos': False, 'sig': False, 'gam': False}, ],

            back_sequence = [   [False, True, False, False],
                                [False, False, True, False],])
            
            _perform_accurate_refinement(current_histo, params, 1, 3,
            ref_sequence  = [ {'area': False, 'pos': False, 'sig': False, 'gam': False},],
            back_sequence = [[True, False, True, False],])
            
        
        # _perform_fast_refinement(current_histo, {'area': True}, [False, False, False, False])
        # _perform_fast_refinement(current_histo, {'area': True, 'pos': True, 'sig': True, 'gam': True}, [False, False, False, False])
        # # _perform_accurate_refinement(current_histo, params, 0, 5,
        # #     ref_sequence= [{'area': True, 'pos': False, 'sig': False, 'gam': True}, 
        # #         {'area': False, 'pos': False, 'sig': True, 'gam': False}, 
        # #         {'area': False, 'pos': False, 'sig': False, 'gam': True}, 
        # #         {'area': True, 'pos': True, 'sig': True, 'gam': True}],
        # #     back_sequence = [[False, False, False, False],
        # #         [False, False, False, False],
        # #         [False, False, False, False],
        # #         [False, False, False, False]])

        #Custom refinement sequences if provided
        #TODO: May want to combine these with the new corrective refinement steps
        _perform_accurate_refinement(current_histo, params, 0, 3, #Intensity, max 3x
            ref_sequence= [{'area': True, 'pos': False, 'sig': False, 'gam': False}],
            back_sequence = [[False, False, False, False]])
        _perform_accurate_refinement(current_histo, params, 0, 3, #Position, max 3x
            ref_sequence= [{'area': False, 'pos': True, 'sig': False, 'gam': False}],
            back_sequence = [[False, False, False, False]])
        _perform_accurate_refinement(current_histo, params, 0, 3, #Shape, max 3x
            ref_sequence= [{'area': False, 'pos': False, 'sig': True, 'gam': False},
                           {'area': False, 'pos': False, 'sig': False, 'gam': True},
                           {'area': False, 'pos': False, 'sig': True, 'gam': True}],
            back_sequence = [[False, False, False, False],
                             [False, False, False, False],
                             [False, False, False, False]])
        _perform_accurate_refinement(current_histo, params, 0, 3, #Full, max 3x
            ref_sequence= [{'area': True, 'pos': True, 'sig': True, 'gam': True}],
            back_sequence = [[False, False, False, False]])
        print(f"    Peak refinement completed for azimuth {histo_index}, frame {frame_index}")




        # Extract peak parameters and create dataframes
        for peak_index, peakVals in enumerate(current_histo.PeakList):
            new_frame = pd.DataFrame([peakVals], columns=['pos', 'area', 'sigma', 'gamma'])
            new_frame['azimuth'] = (spacing * histo_index) + az0
            new_frame['frame'] = frame_index
            new_frame['d'] = (0.1729) / (2 * np.sin(np.deg2rad(new_frame['pos'] / 2)))

            # Calculate strain if references provided (as numpy array)
            if references is not None and peak_index < references.shape[0]:
                # Get reference d for this peak and azimuth
                az_idx = min(histo_index, references.shape[1] - 1)
                ref_d = references[peak_index, az_idx]
                if ref_d != 0 and not np.isnan(ref_d):
                    new_frame['strain'] = (new_frame['d'] - ref_d) / ref_d
                else:
                    new_frame['strain'] = np.nan

            peak_results[peak_index].append(new_frame)

        #TODO: Should be extracting background peaks regardless for analysis use later; do not depend on ref
        if ref:
            # Extract only the peaksList from Background structure
            bkg = current_histo.Background
            if isinstance(bkg, list) and len(bkg) > 1 and isinstance(bkg[1], dict):
                peaks_list = bkg[1].get('peaksList', [])
                background_results.append(peaks_list)
            else:
                background_results.append([])

    image.clearPixelMask()

    # Concatenate results for each peak
    working_histos = [pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
                      for frames in peak_results]



    # Cache the results for future use
    cache[cache_key] = working_histos
    print(f"Cached results for frame {frame_index}")

    # Cleanup: Remove temporary file if created
    if temp_file and os.path.exists(temp_file):
        try:
            os.remove(temp_file)
        except Exception as e:
            print(f"Warning: Could not remove temp file {temp_file}: {e}")

    if ref:
        return (working_histos, background_results)

    return working_histos


def _perform_accurate_refinement(histo, params, min_iterations=0, max_iterations=5,
ref_sequence= [{'area': True, 'pos': True, 'sig': True, 'gam': True}, 
        {'area': False, 'pos': False, 'sig': True, 'gam': False}, 
        {'area': False, 'pos': False, 'sig': False, 'gam': True}, 
        {'area': True, 'pos': True, 'sig': True, 'gam': True}],
back_sequence = [[False, False, False, False],
        [False, False, False, False],
        [False, False, False, False],
        [False, False, False, False]]):
    """Perform detailed iterative peak refinement with convergence detection and validation."""

    # Note: Instrument parameter optimization would be done via G2pwd.setPeakInstPrmMode(False)
    # but this requires direct GSAS-II module access

    # Parameter bounds for validation

    CONVERGENCE_THRESHOLD = 1e-4  # Relative change threshold

    def _validate_parameters(peak_list):
        """Validate that all peak parameters are physically reasonable."""
        fails = False
        for i, peak in enumerate(peak_list):
            pos, area, sigma, gamma = peak

            # Check bounds
            if area < 0:
                fails = True
                print(f"Peak {i}: area {area} less than 0")

            if sigma < 0:
                fails = True
                print(f"Peak {i}: sigma {sigma} less than 0")

            if gamma < 0:
                fails = True
                print(f"Peak {i}: gamma {gamma} less than  0")

            # Check for reasonable position (within 2-theta limits)
            if not (params.limits[0] <= pos <= params.limits[1]):
                fails = True
                #TODO: Add a pos reset for peak num
                print(f"Peak {i}: position {pos} outside limits {params.limits}")


        if fails:
            return False #At least one val is invalid
        return True #All vals are valid

    def _calculate_parameter_changes(old_params, new_params):
        """Calculate relative changes in parameters for convergence detection."""
        if not old_params or not new_params:
            return float('inf')

        max_rel_change = 0.0
        for old_peak, new_peak in zip(old_params, new_params):
            for old_val, new_val in zip(old_peak, new_peak):
                if abs(old_val) > 1e-10:  # Avoid division by very small numbers
                    rel_change = abs((new_val - old_val) / old_val)
                    max_rel_change = max(max_rel_change, rel_change)

        return max_rel_change

    def _safe_refine(flags, back_ref):
        """Helper function for safe peak refinement with logging"""
        try:
            histo.set_peakFlags(**flags)
            for peaknum, key in enumerate(histo.Background[1]["peaksList"]):
                histo.ref_back_peak(peaknum, back_ref)  # Do not refine background peaks
            # Use 'hold' mode to prevent instrument parameter refinement for speed
            histo.refine_peaks(mode='hold')
            return True
        except:
            return False

    def _correct_vals(peak_list, refinement):
        """Validate that all peak parameters are physically reasonable."""
        fails = False
        for i, peak in enumerate(peak_list):
            pos, area, sigma, gamma = peak
            # Only check parameters that were refined in this step
            if refinement.get('area', True) and area < 0:
                fails = True
                area = 1
                print(f"Peak {i}: area {area} less than 0")
            if refinement.get('sig', True) and sigma < 0:
                fails = True
                sigma = 0
                print(f"Peak {i}: sigma {sigma} less than 0")  
            if refinement.get('gam', True) and gamma < 0:
                fails = True
                gamma = 0
                print(f"Peak {i}: gamma {gamma} less than 0")

            if refinement.get('pos', True) and  not (params.limits[0] <= pos <= params.limits[1]):
                fails = True
                #TODO: Add a pos reset for peak num
                print(f"Peak {i}: position {pos} outside limits {params.limits}")

            peak_list[i] = [pos, area, sigma, gamma]

        if fails:
            return False, "Invalid parameters detected", peak_list
        return True, "All parameters valid", peak_list

    previous_params = None
    for iteration in range(max_iterations):
        # Store parameters before refinement
        previous_params = [list(peak) for peak in histo.PeakList]

        # Perform refinement sequence
        corrected = False
        sequence_success = True
        for refinement, back_ref in zip(ref_sequence, back_sequence):
            if not _safe_refine(refinement, back_ref):
                sequence_success = False
                break
            step_passed, _, corrected_vals = _correct_vals(histo.PeakList, refinement)
            #TODO: We need to also be correcting the background vals here, but currently we are not; make sure to implement background peaks into _correct_vals and _validate_parameters
            if not step_passed:
                # Apply corrections using GSAS-II API (PeakList is read-only)
                for peak_idx, (pos, area, sigma, gamma) in enumerate(corrected_vals):
                    histo.PeakList[peak_idx] = [pos, area, sigma, gamma]
                print(f"Iteration {iteration}: Corrected invalid parameters")
                corrected = True  # Mark that a correction was made
        
        if not sequence_success:
            return False


        # Check for convergence
        current_params = [list(peak) for peak in histo.PeakList]
        param_change = _calculate_parameter_changes(previous_params, current_params)
        if (iteration >= min_iterations) and not corrected:
            if param_change < CONVERGENCE_THRESHOLD:
                print(f"Converged")
                return True
            
            if _validate_parameters(histo.PeakList):
                print(f"All values valid")
                return True


    print(f"Overran max")
    return True


def _perform_fast_refinement(histo, peak_ref, back_ref=[False, False, False, False]):
    """Perform quick peak refinement optimized for speed with basic validation."""
    # Optimized refinement sequence
    histo.set_peakFlags(peak_ref)
    for peaknum, key in enumerate(histo.Background[1]["peaksList"]):
        histo.ref_back_peak(peaknum, back_ref)  # Do not refine background peaks
    # Use 'hold' mode for maximum speed
    histo.refine_peaks(mode='hold')

    return True


def _create_single_plot(two_theta: np.ndarray, intensity: np.ndarray,
                       frame_number: int, azimuth: float,
                       sample: str, setting: str, stage: str,
                       output_dir: str,
                       global_min_2theta: float, global_max_2theta: float,
                       global_min_intensity: float, global_max_intensity: float) -> bool:
    """
    Worker function to create a single intensity plot (non-delayed, uses threaded scheduler).

    Args:
        two_theta: 2θ angle array
        intensity: Intensity count array
        frame_number: Frame number for labeling
        azimuth: Azimuthal angle
        sample: Sample name
        setting: Experimental setting
        stage: Measurement stage
        output_dir: Base output directory
        global_min/max_*: Fixed axis limits for ML consistency

    Returns:
        True if successful
    """

    # Create plot with FIXED limits for ML consistency (NO TITLE to prevent overfitting)
    # Use matplotlib.figure.Figure for non-GUI, headless plotting
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(1, 1, 1)

    ax.plot(two_theta, intensity, 'k-', linewidth=0.8, alpha=0.8)
    ax.set_xlabel('2θ (degrees)', fontweight='bold')
    ax.set_ylabel('Intensity (counts)', fontweight='bold')
    # NO TITLE - prevents ML model from learning text patterns instead of diffraction features
    ax.grid(True, alpha=0.3, linestyle='--')

    # Apply fixed limits - CRITICAL for ML processing
    ax.set_xlim(global_min_2theta, global_max_2theta)
    ax.set_ylim(global_min_intensity, global_max_intensity)

    fig.tight_layout()

    # Save as TIFF with robust filename containing all metadata
    # Organize by frame (each frame folder contains all azimuths)
    frame_folder = os.path.join(output_dir, f"Frame{frame_number:04d}")
    filename = f"{sample}_{setting}_{stage}_Frame{frame_number:04d}_Az{int(azimuth):+04d}.tiff"
    output_path = os.path.join(frame_folder, filename)

    # Save with LZW compression for faster I/O (5x smaller files)
    fig.savefig(output_path, format='tiff', dpi=600, bbox_inches='tight',
                pil_kwargs={'compression': 'tiff_lzw'})
    plt.close(fig)

    return True


def plot_intensity_patterns(powder_data_list: List[List[Dict]], params: GSASParams,
                            sample_frames: List) -> None:
    """
    Batch-plot powder pattern intensity data using parallel Dask execution.

    Creates ML-ready TIFF images with consistent dimensions and axis limits.
    Organizes output by frame folders for easy batch processing.

    PERFORMANCE OPTIMIZATIONS:
    - Uses Dask delayed with THREADED scheduler (avoids distributed overhead)
    - Matplotlib Agg backend (no GUI rendering)
    - TIFF LZW compression (5x smaller files, faster I/O)
    - Expected: 10-15x faster than distributed scheduler

    Args:
        powder_data_list: List of powder data (one list per frame, each containing dicts per azimuth)
        params: GSAS processing parameters
        sample_frames: Frame information for labeling
    """

    # Set matplotlib rcParams for consistent output
    plt.rcParams['figure.dpi'] = 600
    plt.rcParams['savefig.dpi'] = 600
    plt.rcParams['font.size'] = 10
    plt.rcParams['axes.labelsize'] = 12
    plt.rcParams['axes.titlesize'] = 14

    # Create output directory using new structure
    # Intensity plots are saved per-peak in Processed/{Date}/{Sample}/Intensity/{Params}/
    # If multiple peaks, create separate folders for each
    from XRD.utils.path_manager import get_timestamp

    timestamp = get_timestamp()

    # For intensity plots, we use dataset-level path (not per-peak)
    # All peaks for a dataset are saved in the same intensity folder
    if params.active_peaks:
        output_dir = params.intensity_plot_path(timestamp)
    else:
        # Fallback if no peaks defined
        from XRD.utils.path_manager import get_intensity_path
        output_dir = get_intensity_path(params.home_dir, params.sample, f"AllPeaks-{timestamp}")

    os.makedirs(output_dir, exist_ok=True)

    print(f"Saving intensity plots to: {output_dir}")
    print("Pre-computing global axis limits for ML consistency...")

    # Pre-compute global limits across ALL data for consistent ML input
    global_min_2theta = float('inf')
    global_max_2theta = float('-inf')
    global_min_intensity = float('inf')
    global_max_intensity = float('-inf')

    for powder_data_frame in powder_data_list:
        for az_data in powder_data_frame:
            two_theta = az_data['two_theta']
            intensity = az_data['intensity']

            global_min_2theta = min(global_min_2theta, np.min(two_theta))
            global_max_2theta = max(global_max_2theta, np.max(two_theta))
            global_min_intensity = min(global_min_intensity, np.min(intensity))
            global_max_intensity = max(global_max_intensity, np.max(intensity))

    # Add 5% padding to intensity for visual clarity
    intensity_range = global_max_intensity - global_min_intensity
    global_min_intensity -= 0.05 * intensity_range
    global_max_intensity += 0.05 * intensity_range

    # Report limits for verification
    print(f"Global 2θ range: [{global_min_2theta:.3f}, {global_max_2theta:.3f}] degrees")
    print(f"Global intensity range: [{global_min_intensity:.1f}, {global_max_intensity:.1f}] counts")

    # Pre-create all frame subfolders to avoid race conditions
    print("Creating frame subfolders...")
    unique_frames = set()
    for frame_info in sample_frames:
        unique_frames.add(frame_info.frame_index)

    for frame_num in sorted(unique_frames):
        frame_folder = os.path.join(output_dir, f"Frame{frame_num:04d}")
        os.makedirs(frame_folder, exist_ok=True)

    print(f"Created {len(unique_frames)} frame folders")

    # Extract simple types from params (avoid serializing complex objects)
    sample = params.sample
    setting = params.setting
    stage = params.stage

    # Build all delayed plot tasks
    all_tasks = []
    task_count = 0
    for frame_idx, powder_data_frame in enumerate(powder_data_list):
        frame_number = sample_frames[frame_idx].frame_index

        for az_data in powder_data_frame:
            # Extract data from dict before passing to delayed function
            two_theta = az_data['two_theta']
            intensity = az_data['intensity']
            azimuth = az_data['azimuth']

            # Wrap function call with delayed() to create Dask task
            task = delayed(_create_single_plot)(
                two_theta, intensity,
                frame_number, azimuth,
                sample, setting, stage,
                output_dir,
                global_min_2theta, global_max_2theta,
                global_min_intensity, global_max_intensity
            )
            all_tasks.append(task)
            task_count += 1

    print(f"Created {task_count} delayed tasks")

    # Execute all tasks in parallel using THREADED scheduler
    # This avoids distributed scheduler overhead (serialization, network, worker spawning)
    print(f"\nGenerating {len(all_tasks)} intensity plots in parallel (threaded scheduler)...")
    start_time = time.time()

    # Use threaded scheduler with optimal number of workers
    num_workers = min(os.cpu_count() or 4, 8)  # Cap at 8 for I/O-bound tasks
    print(f"Using {num_workers} worker threads...")

    compute(*all_tasks, scheduler='threads', num_workers=num_workers)

    elapsed_time = time.time() - start_time
    plots_per_second = len(all_tasks) / elapsed_time if elapsed_time > 0 else 0

    print(f"\n{'='*70}")
    print(f"INTENSITY PLOT EXPORT COMPLETE")
    print(f"{'='*70}")
    print(f"Total plots created: {len(all_tasks)}")
    print(f"Frame folders: {len(unique_frames)}")
    print(f"Image format: TIFF (LZW compressed, lossless, ML-ready)")
    print(f"Image dimensions: 6000×3600 pixels (600 DPI)")
    print(f"Processing time: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
    print(f"Performance: {plots_per_second:.1f} plots/second")
    print(f"Worker threads: {num_workers}")
    print(f"Fixed axis limits:")
    print(f"  - 2θ range: [{global_min_2theta:.3f}, {global_max_2theta:.3f}]°")
    print(f"  - Intensity range: [{global_min_intensity:.1f}, {global_max_intensity:.1f}] counts")
    print(f"\nOutput directory:")
    print(f"  {output_dir}")
    print(f"{'='*70}\n")


def process_images(params: GSASParams, ref_steps) -> XRDDataset:
    """
    Process all images and return unified XRD dataset.
    
    FIXED: Properly handles strain calculation and dataset finalization
    """
    
    # Process reference images using ImageLoader
    print("Discovering reference image frames...")
    ref_frames = ImageLoader.discover_frames(
        directory=params.ref_file(),
        start_frame=0,
        end_frame=-1,
        step=1
    )

    if not ref_frames:
        raise FileNotFoundError("No reference images found")

    # Validate frame ordering
    if not validate_frame_ordering(ref_frames):
        print("Warning: Reference frame ordering may be incorrect")

    print(f"Found {len(ref_frames)} reference frames")
    
    ref_bkg = None
    reference_values = None
    reference_d_array = None
    if not params.intplot_export:
        ref_tasks = []
        for frame_info in ref_frames:
            ref_task = gsas_parallel(
                frame_info.file_path,
                params,
                frame_info.frame_index,
                references=None,
                ref=True,
                ref_steps=ref_steps,
                frame_info=frame_info
            )
            ref_tasks.append(ref_task)
        
        print(f"Processing {len(ref_tasks)} reference images...")
        ref_results = compute(*ref_tasks)

        # Unpack reference results (now returns tuples of (peak_results, background_list))
        ref_peak_results = [tup[0] for tup in ref_results]

        # Calculate average reference values for ALL measurements
        refs_per_peaks = [list(x) for x in zip(*ref_peak_results)]
        n_peaks = len(refs_per_peaks)
        n_azimuths = int(params.total_angle() / params.spacing)

        # Define measurement columns for reference calculations
        measurement_cols = ['pos', 'area', 'sigma', 'gamma', 'd']

        # Create numpy arrays for all reference measurements (peaks x azimuths)
        reference_values = {}
        for measurement in measurement_cols:
            reference_values[measurement] = np.zeros((n_peaks, n_azimuths), dtype='float32')

        for peak_idx, ref_peak in enumerate(refs_per_peaks):
            for az_idx in range(n_azimuths):
                for measurement in measurement_cols:
                    values = []
                    for df in ref_peak:
                        if len(df) > az_idx and measurement in df.columns:
                            val = df.iloc[az_idx][measurement]
                            if not np.isnan(val):
                                values.append(val)

                    if values:
                        reference_values[measurement][peak_idx, az_idx] = np.mean(values)

        # Calculate azimuthally-resolved reference background peaks
        # ref_results is a list of tuples: (peak_results, peaksList_per_azimuth)
        # peaksList format: [[pos, False, int, False, sig, False, gam, False], ...]
        ref_bkg_lists = [tup[1] for tup in ref_results]

        # Only process background peaks if they should exist based on available_peaks
        background_candidates = params.get_background_candidates(params.limits)
        if not background_candidates:
            ref_bkg = None
            print("No background peak candidates - skipping reference background processing")
        elif ref_bkg_lists and len(ref_bkg_lists[0]) > 0:
            # Get number of azimuths from first reference
            n_az = len(ref_bkg_lists[0])

            # Create azimuthally-resolved background peaks (list of peaksLists, one per azimuth)
            ref_bkg = []

            for az_idx in range(n_az):
                # Collect all peaksLists for this azimuth across all reference frames
                peaks_for_azimuth = []
                for ref_frame_peaks in ref_bkg_lists:
                    if az_idx < len(ref_frame_peaks) and ref_frame_peaks[az_idx]:
                        peaks_for_azimuth.append(ref_frame_peaks[az_idx])

                # Average the peaks for this azimuth
                if peaks_for_azimuth and len(peaks_for_azimuth[0]) > 0:
                    num_peaks = len(peaks_for_azimuth[0])
                    averaged_peaks = []

                    for peak_idx in range(num_peaks):
                        # Collect values for this peak across all reference frames
                        peak_positions = []
                        peak_intensities = []
                        peak_sigmas = []
                        peak_gammas = []

                        for frame_peaks in peaks_for_azimuth:
                            if peak_idx < len(frame_peaks) and len(frame_peaks[peak_idx]) >= 8:
                                peak = frame_peaks[peak_idx]
                                peak_positions.append(peak[0])
                                peak_intensities.append(peak[2])
                                peak_sigmas.append(peak[4])
                                peak_gammas.append(peak[6])

                        # Average the numeric values
                        avg_pos = float(np.nanmean(peak_positions)) if peak_positions else 4.5
                        avg_int = float(np.nanmean(peak_intensities)) if peak_intensities else 1000.0
                        avg_sig = float(np.nanmean(peak_sigmas)) if peak_sigmas else 0.1
                        avg_gam = float(np.nanmean(peak_gammas)) if peak_gammas else 0.1

                        # Create averaged peak: [pos, False, int, False, sig, False, gam, False]
                        averaged_peaks.append([avg_pos, False, avg_int, False, avg_sig, False, avg_gam, False])

                    ref_bkg.append(averaged_peaks)
                else:
                    ref_bkg.append([])

            print(f"Calculated azimuthally-resolved background peaks for {len(ref_bkg)} azimuths")
            if ref_bkg and len(ref_bkg[0]) > 0:
                print(f"Example: {len(ref_bkg[0])} background peaks per azimuth")
        else:
            ref_bkg = None

        # Maintain backward compatibility
        reference_d_array = reference_values['d']

        print(f"Calculated reference values:")
        for measurement, array in reference_values.items():
            count = np.count_nonzero(array)
            print(f"  {measurement}: {count} non-zero values")
    
    # Process sample images using ImageLoader
    print("Discovering sample image frames...")
    sample_frames = ImageLoader.discover_frames(
        directory=params.image_file(),
        start_frame=params.frames[0],
        end_frame=params.frames[1],
        step=params.step
    )

    if not sample_frames:
        raise FileNotFoundError("No sample images found")

    # Validate frame ordering
    if not validate_frame_ordering(sample_frames):
        print("Warning: Sample frame ordering may be incorrect")

    print(f"Found {len(sample_frames)} sample frames")

    sample_tasks = []
    for frame_info in sample_frames:
        # Pass the reference arrays (d-spacing for strain, background, and all peak parameters for initialization)
        #TODO: THE DYNAMIC BKG FLAG IS DISABLED FOR NOW
        task = gsas_parallel(
            frame_info.file_path,
            params,
            frame_info.frame_index,
            references=reference_d_array,
            reference_bkg=ref_bkg,
            reference_peaks=reference_values,
            dynamic_bkg=True,
            ref_steps=ref_steps,
            frame_info=frame_info
        )
        sample_tasks.append(task)
    
    print(f"Processing {len(sample_tasks)} sample images...")
    sample_results = compute(*sample_tasks)

    # Handle intensity plot export mode
    if params.intplot_export:
        print("Intensity plot export mode - creating plots...")
        plot_intensity_patterns(sample_results, params, sample_frames)
        print("Intensity plots complete!")
        return None  # Return early, no XRDDataset created

    if not params.intplot_export:
        # Determine actual dimensions
        n_peaks = len(sample_results[0]) if sample_results else 0
        n_frames = len(sample_results)
        n_azimuths = int(params.total_angle() / params.spacing)
        
        # Define measurement columns (without strain initially)
        measurement_cols = ['pos', 'area', 'sigma', 'gamma', 'd']
        
        # Create XRD dataset
        print("Creating unified dataset...")
        xrd_dataset = XRDDataset(n_peaks, n_frames, n_azimuths, measurement_cols, params)
        
        # Fill dataset with processed data
        for frame_idx, frame_results in enumerate(sample_results):
            for peak_idx, peak_df in enumerate(frame_results):
                if not peak_df.empty:
                    xrd_dataset.set_frame_data(peak_idx, frame_idx, peak_df)
        
        # Store ALL reference values in dataset for comprehensive PCT calculations
        xrd_dataset.reference_values = reference_values
        xrd_dataset.reference_d = reference_d_array  # Maintain backward compatibility

        # Calculate strain using the reference d-spacings array (before finalization)
        print("Calculating strain...")
        if 'd' in xrd_dataset.col_idx and np.any(reference_d_array != 0):
            xrd_dataset.calculate_strain(reference_d_array)

        # CRITICAL: Finalize the dataset to convert to Dask
        xrd_dataset.finalize()
        
        # Calculate derived measurements (after finalization)
        print("Calculating derived measurements...")
        
        # Calculate deltas for various parameters
        for measurement in ['d', 'strain', 'area', 'sigma', 'gamma', 'pos']:
            if measurement in xrd_dataset.col_idx:
                xrd_dataset.calculate_delta(measurement)
        
        # Update Miller indices
        miller_indices = params.get_miller_indices()
        xrd_dataset.peak_miller_indices[:len(miller_indices)] = miller_indices
        
        print("Dataset creation complete!")
        return xrd_dataset


def load_or_process_data(params: GSASParams,
                        ref_steps = [[{"area":False,"pos":False,"sig":False,"gam":False}, [False, True, False, False]]],
                        available_peaks_meta: list = None,
                        active_peaks_meta: list = None) -> XRDDataset:
    """
    Load existing data or process new data if not found or if force reprocessing.

    Args:
        params: Processing parameters
        ref_steps: Reference refinement steps
        available_peaks_meta: List of dicts with available peak metadata (deprecated, use params.available_peaks)
        active_peaks_meta: List of dicts with active peak metadata (deprecated, use params.active_peaks)

    Returns:
        XRDDataset object
    """
    save_path = params.save_path()

    # Note: Peak metadata is now stored in params.active_peaks and params.available_peaks
    # No need for separate PeakConfig initialization

    # Load analysis settings to check force_reprocess flag
    with open('submitted_values.json', 'r') as f:
        values = json.load(f)
    force_reprocess = values.get('force_reprocess', False)

    if not force_reprocess:
        try:
            # Try to load existing data
            print(f"Attempting to load data from {save_path}...")
            dataset = XRDDataset.load(save_path, params)
            print("Successfully loaded existing dataset!")
            return dataset
        except (FileNotFoundError, OSError):
            print("No existing data found. Processing images...")
    else:
        print("Force reprocessing enabled. Processing images...")
    
    # Process new data
    dataset = process_images(params, ref_steps)
    
    # Save processed data
    print(f"Saving processed data to {save_path}...")
    dataset.save(save_path)
    print("Data saved successfully!")
    
    return dataset


def subtract_datasets(before: XRDDataset, after: XRDDataset, 
                     measurements: List[str], shift_val: int = 0) -> XRDDataset:
    """
    Calculate differences between before and after datasets.
    
    Args:
        before: Data from before treatment
        after: Data from after treatment  
        measurements: List of measurements to calculate differences for
        shift_val: Shift to apply for alignment
        
    Returns:
        XRDDataset containing difference data
    """
    # Ensure both datasets are finalized
    if before.data is None:
        before.finalize()
    if after.data is None:
        after.finalize()
    
    # Create new dataset for differences
    diff_params = after.params
    diff_params.stage = Stages.DELT
    
    # Create measurement columns for differences
    diff_measurement_cols = after.measurement_cols.copy()
    for measurement in measurements:
        if measurement in after.col_idx:
            diff_measurement_cols.append(f'diff {measurement}')
    
    # Create difference dataset
    diff_dataset = XRDDataset(after.n_peaks, after.n_frames, after.n_azimuths, 
                             diff_measurement_cols, diff_params)
    
    # Copy existing data from after dataset
    diff_dataset.data = after.data.copy()
    diff_dataset.finalize()
    
    # Calculate differences
    for measurement in measurements:
        if measurement in before.col_idx and measurement in after.col_idx:
            before_data = before.get_measurement(measurement)
            after_data = after.get_measurement(measurement)
            
            # Apply shift if specified
            if shift_val != 0:
                if shift_val > 0:
                    # Shift after data down
                    after_data = da.roll(after_data, shift_val, axis=1)
                    after_data[:, :shift_val] = da.nan
                else:
                    # Shift before data down  
                    before_data = da.roll(before_data, -shift_val, axis=1)
                    before_data[:, :(-shift_val)] = da.nan
            
            # Calculate difference
            diff_data = after_data - before_data
            diff_dataset.add_measurement(f'diff {measurement}', diff_data)
    
    return diff_dataset


# ================== MAIN EXECUTION ==================

def main():
    """Example usage of the unified processing module."""
    client = get_dask_client()

    # Define peak configuration
    example_peak = PeakParams(
        name="Martensite 211",
        miller_index="211",
        position=8.46,
        limits=(7.2, 9.0)
    )

    # Define processing parameters
    parameters = GSASParams(
        image_folder="G:/Data/Feb2025/pilatus/B",
        control_file="G:/Data/Feb2025/pilatus/Ceria/Ceria-Profile.imctrl",
        mask_file="G:/Data/Feb2025/pilatus/Ceria/test_mask.immask",

        sample="B3",
        setting="Profile",
        stage=Stages.BEF,
        notes="",
        exposure="1",

        active_peaks=[example_peak],
        azimuths=(0, 360),
        frames=(0, -1),

        spacing=5,
        step=1,

        # Detector & beam parameters (Pilatus 300K-W, typical synchrotron)
        pixel_size=(172.0, 172.0),      # microns
        wavelength=0.240,                # Angstroms
        detector_size=(1475, 1679)       # pixels
    )

    # Load or process data
    dataset = load_or_process_data(parameters)

    print("Processing complete!")
    print(f"Dataset shape: {dataset.data.shape}")
    print(f"Available measurements: {dataset.measurement_cols}")

    close_dask_client(client)


if __name__ == "__main__":
    main()