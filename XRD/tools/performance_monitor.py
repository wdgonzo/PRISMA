#!/usr/bin/env python3
"""
Performance Monitoring and Benchmarking Tool
============================================
Performance monitoring and benchmarking tools for XRD processing system.

This module provides comprehensive performance analysis, benchmarking,
and optimization validation for HPC deployment.

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import time
import psutil
import numpy as np
import pandas as pd
import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from contextlib import contextmanager

@dataclass
class PerformanceMetrics:
    """Container for performance measurement data."""
    operation: str
    duration: float
    memory_peak: float
    memory_start: float
    cpu_percent: float
    io_read_mb: float
    io_write_mb: float
    cache_hits: int = 0
    cache_misses: int = 0

class PerformanceMonitor:
    """
    Comprehensive performance monitoring system for XRD processing.

    Tracks timing, memory usage, I/O, and system resources during processing.
    """

    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.start_time: float = 0
        self.process = psutil.Process()

    def clear_metrics(self):
        """Clear all collected metrics."""
        self.metrics.clear()

    @contextmanager
    def monitor_operation(self, operation_name: str):
        """
        Context manager for monitoring a specific operation.

        Usage:
            with monitor.monitor_operation("peak_fitting"):
                # Your code here
                pass
        """
        # Initial measurements
        start_time = time.time()
        start_memory = self.process.memory_info().rss / (1024**2)  # MB
        start_io = self.process.io_counters()

        # Start CPU monitoring
        self.process.cpu_percent()  # Initialize CPU monitoring

        try:
            yield
        finally:
            # Final measurements
            end_time = time.time()
            end_memory = self.process.memory_info().rss / (1024**2)  # MB
            end_io = self.process.io_counters()
            cpu_percent = self.process.cpu_percent()

            # Calculate metrics
            duration = end_time - start_time
            memory_peak = max(start_memory, end_memory)
            io_read_mb = (end_io.read_bytes - start_io.read_bytes) / (1024**2)
            io_write_mb = (end_io.write_bytes - start_io.write_bytes) / (1024**2)

            # Store metrics
            metric = PerformanceMetrics(
                operation=operation_name,
                duration=duration,
                memory_peak=memory_peak,
                memory_start=start_memory,
                cpu_percent=cpu_percent,
                io_read_mb=io_read_mb,
                io_write_mb=io_write_mb
            )

            self.metrics.append(metric)

    def get_summary(self) -> Dict:
        """Get summary statistics of all monitored operations."""
        if not self.metrics:
            return {"error": "No metrics collected"}

        total_time = sum(m.duration for m in self.metrics)
        total_memory = max(m.memory_peak for m in self.metrics)
        total_io_read = sum(m.io_read_mb for m in self.metrics)
        total_io_write = sum(m.io_write_mb for m in self.metrics)

        # Group by operation type
        operation_stats = {}
        for metric in self.metrics:
            if metric.operation not in operation_stats:
                operation_stats[metric.operation] = []
            operation_stats[metric.operation].append(metric)

        # Calculate per-operation statistics
        operation_summary = {}
        for op_name, op_metrics in operation_stats.items():
            durations = [m.duration for m in op_metrics]
            operation_summary[op_name] = {
                'count': len(op_metrics),
                'total_time': sum(durations),
                'avg_time': np.mean(durations),
                'min_time': min(durations),
                'max_time': max(durations),
                'std_time': np.std(durations)
            }

        return {
            'total_operations': len(self.metrics),
            'total_time_sec': total_time,
            'peak_memory_mb': total_memory,
            'total_io_read_mb': total_io_read,
            'total_io_write_mb': total_io_write,
            'operations': operation_summary
        }

    def save_report(self, filepath: str):
        """Save detailed performance report to JSON file."""
        summary = self.get_summary()

        # Add system information
        system_info = {
            'cpu_count': psutil.cpu_count(),
            'memory_gb': psutil.virtual_memory().total / (1024**3),
            'python_version': os.sys.version,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        # Detailed metrics
        detailed_metrics = []
        for metric in self.metrics:
            detailed_metrics.append({
                'operation': metric.operation,
                'duration': metric.duration,
                'memory_peak_mb': metric.memory_peak,
                'memory_start_mb': metric.memory_start,
                'cpu_percent': metric.cpu_percent,
                'io_read_mb': metric.io_read_mb,
                'io_write_mb': metric.io_write_mb,
                'cache_hits': metric.cache_hits,
                'cache_misses': metric.cache_misses
            })

        report = {
            'system_info': system_info,
            'summary': summary,
            'detailed_metrics': detailed_metrics
        }

        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)

    def print_summary(self):
        """Print a formatted summary of performance metrics."""
        summary = self.get_summary()

        if 'error' in summary:
            print(f"❌ {summary['error']}")
            return

        print("\n" + "="*60)
        print("📊 PERFORMANCE MONITORING SUMMARY")
        print("="*60)

        print(f"Total Operations: {summary['total_operations']}")
        print(f"Total Time: {summary['total_time_sec']:.2f} seconds")
        print(f"Peak Memory: {summary['peak_memory_mb']:.1f} MB")
        print(f"I/O Read: {summary['total_io_read_mb']:.1f} MB")
        print(f"I/O Write: {summary['total_io_write_mb']:.1f} MB")

        print(f"\n📈 OPERATION BREAKDOWN:")
        for op_name, stats in summary['operations'].items():
            print(f"\n{op_name.upper()}:")
            print(f"  Count: {stats['count']}")
            print(f"  Total: {stats['total_time']:.2f}s")
            print(f"  Average: {stats['avg_time']:.3f}s")
            print(f"  Range: {stats['min_time']:.3f}s - {stats['max_time']:.3f}s")
            if stats['std_time'] > 0:
                print(f"  Std Dev: {stats['std_time']:.3f}s")

class PerformanceBenchmark:
    """
    Benchmarking suite for validating optimization improvements.
    """

    @staticmethod
    def benchmark_zarr_compression(test_data_size_mb: int = 100) -> Dict:
        """Benchmark Zarr compression performance."""
        import zarr
        from zarr.codecs import BloscCodec, BloscCname, BloscShuffle
        import numcodecs
        import tempfile
        import shutil

        # Create test data similar to XRD patterns
        np.random.seed(42)
        n_elements = int(test_data_size_mb * 1024 * 1024 / 4)  # float32
        test_data = np.random.random(n_elements).astype(np.float32)
        test_data = test_data.reshape(-1, 8)  # Similar to measurement columns

        results = {}

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Test v3 BloscCodec
            try:
                v3_codec = BloscCodec(
                    cname=BloscCname.zstd,
                    clevel=3,
                    shuffle=BloscShuffle.shuffle,
                    typesize=4
                )

                start_time = time.time()
                if hasattr(zarr, '__version__') and zarr.__version__.startswith('3'):
                    zarr.save_array(f"{tmp_dir}/v3_test.zarr", test_data, codecs=[v3_codec])
                else:
                    # Fallback
                    zarr.save_array(f"{tmp_dir}/v3_test.zarr", test_data, compressor=v3_codec)
                v3_time = time.time() - start_time

                # Calculate compression ratio
                compressed_size = sum(
                    os.path.getsize(os.path.join(root, file))
                    for root, dirs, files in os.walk(f"{tmp_dir}/v3_test.zarr")
                    for file in files
                )

                results['zarr_v3'] = {
                    'compression_time': v3_time,
                    'compression_ratio': 1 - (compressed_size / test_data.nbytes),
                    'throughput_mbps': test_data_size_mb / v3_time
                }

            except Exception as e:
                results['zarr_v3'] = {'error': str(e)}

            # Test v2 numcodecs.Blosc
            try:
                v2_codec = numcodecs.Blosc(cname='zstd', clevel=3, shuffle=numcodecs.Blosc.SHUFFLE)

                start_time = time.time()
                zarr.save_array(f"{tmp_dir}/v2_test.zarr", test_data, compressor=v2_codec)
                v2_time = time.time() - start_time

                # Calculate compression ratio
                compressed_size = sum(
                    os.path.getsize(os.path.join(root, file))
                    for root, dirs, files in os.walk(f"{tmp_dir}/v2_test.zarr")
                    for file in files
                )

                results['zarr_v2'] = {
                    'compression_time': v2_time,
                    'compression_ratio': 1 - (compressed_size / test_data.nbytes),
                    'throughput_mbps': test_data_size_mb / v2_time
                }

            except Exception as e:
                results['zarr_v2'] = {'error': str(e)}

        return results

    @staticmethod
    def benchmark_dask_chunking(shapes: List[Tuple[int, ...]] = None) -> Dict:
        """Benchmark different chunking strategies."""
        import dask.array as da

        if shapes is None:
            shapes = [
                (3, 100, 44, 8),     # Small dataset
                (3, 500, 88, 10),    # Medium dataset
                (3, 1000, 144, 12),  # Large dataset
            ]

        results = {}

        for i, shape in enumerate(shapes):
            dataset_name = f"dataset_{i+1}_{shape}"

            # Create test data
            data = da.random.random(shape, chunks='auto', dtype=np.float32)

            # Test different chunking strategies
            chunk_strategies = {
                'auto': 'auto',
                'small': (1, 10, 10, shape[-1]),
                'medium': (1, 50, 20, shape[-1]),
                'large': (1, min(100, shape[1]), min(44, shape[2]), shape[-1])
            }

            strategy_results = {}

            for strategy_name, chunks in chunk_strategies.items():
                try:
                    rechunked = data.rechunk(chunks)

                    # Measure computation time
                    start_time = time.time()
                    result = da.sum(rechunked).compute()
                    compute_time = time.time() - start_time

                    # Calculate chunk statistics
                    if hasattr(rechunked, 'chunksize'):
                        chunk_mb = np.prod(rechunked.chunksize) * 4 / (1024**2)  # float32
                    else:
                        chunk_mb = 0

                    strategy_results[strategy_name] = {
                        'compute_time': compute_time,
                        'chunk_size_mb': chunk_mb,
                        'num_chunks': rechunked.npartitions if hasattr(rechunked, 'npartitions') else 0
                    }

                except Exception as e:
                    strategy_results[strategy_name] = {'error': str(e)}

            results[dataset_name] = strategy_results

        return results

    @staticmethod
    def run_comprehensive_benchmark() -> Dict:
        """Run all benchmarks and return comprehensive results."""
        print("🏁 Running Comprehensive Performance Benchmark...")

        results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_gb': psutil.virtual_memory().total / (1024**3),
                'python_version': os.sys.version
            }
        }

        # Zarr compression benchmark
        print("   Testing Zarr compression...")
        try:
            results['zarr_compression'] = PerformanceBenchmark.benchmark_zarr_compression()
        except Exception as e:
            results['zarr_compression'] = {'error': str(e)}

        # Dask chunking benchmark
        print("   Testing Dask chunking strategies...")
        try:
            results['dask_chunking'] = PerformanceBenchmark.benchmark_dask_chunking()
        except Exception as e:
            results['dask_chunking'] = {'error': str(e)}

        return results

if __name__ == "__main__":
    # Run comprehensive benchmark
    benchmark_results = PerformanceBenchmark.run_comprehensive_benchmark()

    # Save results
    report_file = f"benchmark_report_{int(time.time())}.json"
    with open(report_file, 'w') as f:
        json.dump(benchmark_results, f, indent=2)

    print(f"\n✅ Benchmark complete! Results saved to {report_file}")

    # Print summary
    print("\n📊 BENCHMARK SUMMARY:")
    if 'zarr_compression' in benchmark_results:
        zarr_results = benchmark_results['zarr_compression']
        if 'zarr_v3' in zarr_results and 'error' not in zarr_results['zarr_v3']:
            v3_ratio = zarr_results['zarr_v3']['compression_ratio'] * 100
            print(f"   Zarr v3 compression: {v3_ratio:.1f}%")
        if 'zarr_v2' in zarr_results and 'error' not in zarr_results['zarr_v2']:
            v2_ratio = zarr_results['zarr_v2']['compression_ratio'] * 100
            print(f"   Zarr v2 compression: {v2_ratio:.1f}%")