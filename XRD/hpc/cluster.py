"""
HPC Cluster Initialization Module
==================================
Automatic detection and configuration of Dask cluster backends for
local development and HPC (Crux supercomputer) execution.

Features:
- Auto-detects MPI environment (via mpiexec/mpirun)
- Configures Dask-MPI cluster for multi-node HPC execution
- Falls back to LocalCluster for single-node/development
- Optimized settings for Crux supercomputer
- Preserves all HPC memory and compression optimizations

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import os
import sys
import psutil
from typing import Optional, Dict, Any


def is_mpi_environment() -> bool:
    """
    Detect if running in an MPI environment.

    Returns:
        True if MPI environment detected, False otherwise
    """
    # Check for MPI-related environment variables
    mpi_indicators = [
        'PMI_RANK',           # Intel MPI
        'OMPI_COMM_WORLD_RANK',  # OpenMPI
        'MV2_COMM_WORLD_RANK',   # MVAPICH2
        'PMIX_RANK',          # PMIx
        'MPI_LOCALRANKID',    # Various MPI implementations
    ]

    for indicator in mpi_indicators:
        if indicator in os.environ:
            return True

    # Check if mpi4py is available and initialized
    try:
        from mpi4py import MPI
        comm = MPI.COMM_WORLD
        if comm.Get_size() > 1:
            return True
    except (ImportError, Exception):
        pass

    return False


def get_hpc_config() -> Dict[str, Any]:
    """
    Get HPC-optimized Dask configuration.

    Based on CLAUDE.md v1.3 performance optimizations:
    - Memory management for HPC nodes
    - LZ4 compression for network communication
    - Worker timeout settings
    - Thread management to prevent oversubscription

    Returns:
        Dictionary of Dask configuration parameters
    """
    return {
        # Memory management (HPC-tuned)
        'distributed.worker.memory.target': 0.7,      # Use 70% of worker memory
        'distributed.worker.memory.spill': 0.8,       # Spill at 80%
        'distributed.worker.memory.pause': 0.9,       # Pause at 90%
        'distributed.worker.memory.terminate': 0.95,  # Terminate at 95%

        # Network optimization
        'distributed.comm.compression': 'lz4',        # Fast compression for MPI
        'distributed.comm.timeouts.connect': '60s',   # Connection timeout
        'distributed.comm.timeouts.tcp': '60s',       # TCP timeout

        # Worker management
        'distributed.scheduler.worker-ttl': '5 minutes',  # Worker timeout
        'distributed.scheduler.allowed-failures': 3,      # Retry failures

        # Logging (reduce verbosity for HPC)
        'distributed.scheduler.log-length': 1000,
        'distributed.worker.log-length': 1000,
    }


def configure_hpc_environment():
    """
    Configure environment variables for optimal HPC performance.

    Based on CLAUDE.md v1.3 HPC optimization:
    - Prevents thread oversubscription on multi-core nodes
    - Optimizes for Dask's distributed parallelism model
    """
    # Prevent thread oversubscription (critical for HPC)
    os.environ.setdefault('OMP_NUM_THREADS', '1')
    os.environ.setdefault('MKL_NUM_THREADS', '1')
    os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
    os.environ.setdefault('NUMEXPR_NUM_THREADS', '1')

    # Crux-specific proxy settings for compute nodes
    if 'PBS_JOBID' in os.environ:  # Running in PBS job
        os.environ.setdefault('http_proxy', 'http://proxy.alcf.anl.gov:3128')
        os.environ.setdefault('https_proxy', 'http://proxy.alcf.anl.gov:3128')


def get_dask_client(
    n_workers: Optional[int] = None,
    threads_per_worker: Optional[int] = None,
    memory_limit: str = 'auto',
    local_directory: Optional[str] = None,
    verbose: bool = True
):
    """
    Get a Dask client with automatic backend selection.

    Automatically detects execution environment:
    - MPI environment: Creates Dask-MPI cluster for multi-node execution
    - Local/single-node: Creates LocalCluster for development

    Args:
        n_workers: Number of workers (None = auto-detect)
        threads_per_worker: Threads per worker (None = auto-detect)
        memory_limit: Memory limit per worker ('auto' or specific like '16GB')
        local_directory: Temporary directory for worker files
        verbose: Print cluster information

    Returns:
        dask.distributed.Client instance

    Example:
        >>> client = get_dask_client()
        >>> # Automatically uses Dask-MPI on Crux, LocalCluster on laptop
        >>> result = dataset.compute()
        >>> client.close()
    """
    from dask.distributed import Client
    import dask

    # Configure HPC environment
    configure_hpc_environment()

    # Apply HPC-optimized configuration
    hpc_config = get_hpc_config()
    dask.config.update(dask.config.config, hpc_config, priority='new')

    # Detect execution environment
    use_mpi = is_mpi_environment()

    if use_mpi:
        # ============ MPI CLUSTER (Multi-node HPC) ============
        if verbose:
            print("=" * 60)
            print("HPC MODE: Initializing Dask-MPI Cluster")
            print("=" * 60)

        try:
            from dask_mpi import initialize
            from mpi4py import MPI

            # Get MPI information
            comm = MPI.COMM_WORLD
            rank = comm.Get_rank()
            size = comm.Get_size()

            if verbose and rank == 0:
                print(f"MPI Size: {size} processes")
                print(f"Detected MPI implementation via environment")

            # Initialize Dask-MPI
            # One process becomes scheduler, one becomes client, rest become workers
            # Expected workers: size - 2
            initialize(
                nthreads=threads_per_worker or 1,  # Threads per worker
                local_directory=local_directory,   # Temporary storage
                memory_limit=memory_limit,         # Memory per worker
                interface='ib0',                   # Use InfiniBand if available, falls back to eth0
            )

            # Get client (only rank 0 has access)
            client = Client()

            if verbose and rank == 0:
                print(f"Scheduler: 1 process")
                print(f"Client: 1 process (rank 0)")
                print(f"Workers: {size - 2} processes")
                print(f"Threads per worker: {threads_per_worker or 1}")
                print(f"Memory limit per worker: {memory_limit}")
                print(f"Cluster dashboard: {client.dashboard_link}")
                print("=" * 60)

            return client

        except ImportError as e:
            if verbose:
                print(f"WARNING: MPI environment detected but dask-mpi not available: {e}")
                print("Falling back to LocalCluster...")
            use_mpi = False

    # ============ LOCAL CLUSTER (Single-node/Development) ============
    if verbose:
        print("=" * 60)
        print("LOCAL MODE: Initializing LocalCluster")
        print("=" * 60)

    from dask.distributed import LocalCluster

    # Auto-detect optimal settings
    if n_workers is None:
        # Use 75% of available cores (same as GSAS optimization)
        n_workers = max(1, int(os.cpu_count() * 0.75))

    if threads_per_worker is None:
        threads_per_worker = 1  # Avoid thread oversubscription

    # Create local cluster
    cluster = LocalCluster(
        n_workers=n_workers,
        threads_per_worker=threads_per_worker,
        memory_limit=memory_limit,
        local_directory=local_directory,
        silence_logs=False if verbose else True,
    )

    client = Client(cluster)

    if verbose:
        memory_gb = psutil.virtual_memory().total / (1024**3)
        print(f"System Memory: {memory_gb:.1f} GB")
        print(f"CPU Cores: {os.cpu_count()}")
        print(f"Workers: {n_workers}")
        print(f"Threads per worker: {threads_per_worker}")
        print(f"Memory limit per worker: {memory_limit}")
        print(f"Cluster dashboard: {client.dashboard_link}")
        print("=" * 60)

    return client


def close_dask_client(client):
    """
    Properly close Dask client and cleanup resources.

    Args:
        client: Dask Client instance
    """
    if client is not None:
        try:
            client.close()
        except Exception as e:
            print(f"Warning: Error closing Dask client: {e}")


# ================== USAGE EXAMPLES ==================

if __name__ == "__main__":
    """
    Test cluster initialization and display information.
    """
    print("Testing HPC Cluster Initialization")
    print("=" * 60)

    # Test environment detection
    print(f"MPI Environment Detected: {is_mpi_environment()}")
    print(f"PBS Job ID: {os.environ.get('PBS_JOBID', 'Not in PBS job')}")
    print()

    # Initialize client
    client = get_dask_client(verbose=True)

    # Display worker information
    print("\nWorker Information:")
    print(client.scheduler_info())

    # Test basic computation
    import dask.array as da
    print("\nTesting computation:")
    x = da.random.random((10000, 10000), chunks=(1000, 1000))
    result = x.mean().compute()
    print(f"Test computation result: {result:.6f}")

    # Cleanup
    close_dask_client(client)
    print("\nCluster closed successfully")
