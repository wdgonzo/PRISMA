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
    - Auto compression for network communication (Crux requirement)
    - Extended timeout settings for 8K-16K worker scale
    - Thread management to prevent oversubscription
    - Reduced scheduler overhead for massive parallelism

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
        'distributed.comm.compression': 'auto',       # Auto-select best available compression (Crux requirement)
        'distributed.comm.timeouts.connect': '300s',  # Connection timeout (5 min - reduced for faster failure detection)
        'distributed.comm.timeouts.tcp': '300s',      # TCP timeout (5 min)
        'distributed.comm.timeouts.shutdown': '120s', # Shutdown timeout (2 min - reduced for cleaner exits)

        # Heartbeat/ping timeouts (CRITICAL for long-running tasks)
        'distributed.scheduler.worker-heartbeat-interval': '30s',  # How often workers ping scheduler (default: 1s)
        'distributed.scheduler.worker-heartbeat-timeout': '600s',  # Timeout before worker considered dead (10 min - was 120s)

        # Worker management (extended for massive scale)
        'distributed.scheduler.worker-ttl': '5 minutes',  # Worker timeout
        'distributed.scheduler.allowed-failures': 10,      # Allow more transient failures at scale
        'distributed.worker.startup-timeout': '300s',      # Worker startup patience (5 min - reduced)
        'distributed.core.default-connect-timeout': '300s', # Default connection timeout (5 min)

        # Scheduler optimization (reduce overhead for 8K-16K workers)
        'distributed.scheduler.validate': False,           # Skip validation at scale (performance)
        'distributed.scheduler.events-log-length': 1000,   # Reduce event tracking (from default 100000)
        'distributed.admin.log-length': 100,               # Reduce admin logging

        # Scheduler behavior (CRITICAL for massive scale - prevent premature shutdown)
        'distributed.scheduler.idle-timeout': '0',         # Disable idle timeout (never auto-shutdown during initialization)
        'distributed.admin.tick.interval': '100ms',        # Slower ticks for 8K+ workers (reduce overhead)
        'distributed.admin.tick.limit': '10s',             # Allow longer scheduler ticks at scale

        # Logging (minimal for HPC - prevent I/O storms with many workers)
        'distributed.scheduler.log-length': 100,           # Reduced from 1000
        'distributed.worker.log-length': 100,              # Reduced from 1000
    }


def detect_network_interface() -> Optional[str]:
    """
    Detect the best network interface for Dask-MPI communication.

    Priority order:
    1. hsn0/hsn* - HPE Slingshot (Crux, Aurora, etc.)
    2. ib0/ib* - InfiniBand (most HPC systems)
    3. eth0/enp* - Ethernet
    4. None - Let Dask auto-detect

    Returns:
        Network interface name or None for auto-detection
    """
    try:
        import netifaces

        interfaces = netifaces.interfaces()

        # Priority list for HPC networks
        priority_patterns = [
            ('hsn', 'HPE Slingshot'),   # Crux, Aurora
            ('ib', 'InfiniBand'),        # Traditional HPC
            ('eth', 'Ethernet'),         # Standard
            ('enp', 'Ethernet'),         # Predictable naming
        ]

        for pattern, name in priority_patterns:
            for iface in interfaces:
                if iface.startswith(pattern) and iface != 'lo':
                    return iface

    except ImportError:
        # netifaces not available, try psutil
        try:
            import psutil
            interfaces = list(psutil.net_if_addrs().keys())

            # Same priority patterns
            for pattern, _ in [('hsn', ''), ('ib', ''), ('eth', ''), ('enp', '')]:
                for iface in interfaces:
                    if iface.startswith(pattern) and iface != 'lo':
                        return iface
        except:
            pass

    # Let Dask auto-detect
    return None


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

            # Detect optimal network interface for this system
            network_interface = detect_network_interface()

            if verbose and rank == 0:
                if network_interface:
                    print(f"Network interface: {network_interface}")
                else:
                    print(f"Network interface: auto-detect")

            # Initialize Dask-MPI
            # One process becomes scheduler, one becomes client, rest become workers
            # Expected workers: size - 2
            # Dashboard is bound to 0.0.0.0:8787 (accessible via SSH tunnel)
            initialize(
                nthreads=threads_per_worker or 1,  # Threads per worker
                local_directory=local_directory,   # Temporary storage
                memory_limit=memory_limit,         # Memory per worker
                interface=network_interface,       # Auto-detected HPC network (hsn0, ib0, etc.)
                dashboard_address=':8787',         # Bind dashboard to port 8787 on all interfaces
            )

            # Get client (only rank 0 has access)
            client = Client()

            # Wait for all workers to be ready (CRITICAL for massive scale)
            if rank == 0:
                expected_workers = size - 2  # Total ranks minus scheduler and client

                if verbose:
                    print(f"\nWaiting for {expected_workers} workers to initialize...")
                    print(f"This may take several minutes at scale ({size} MPI ranks)")

                # Wait with timeout matching worker startup timeout (10 minutes)
                try:
                    client.wait_for_workers(n_workers=expected_workers, timeout=600)

                    if verbose:
                        actual_workers = len(client.scheduler_info()['workers'])
                        print(f"✓ All {actual_workers} workers ready and connected")
                        print(f"Worker initialization complete")
                except TimeoutError:
                    actual_workers = len(client.scheduler_info()['workers'])
                    print(f"⚠ WARNING: Only {actual_workers}/{expected_workers} workers ready after 10 minutes")
                    print(f"Proceeding with available workers - some may still be initializing")

            if verbose and rank == 0:
                import socket
                hostname = socket.gethostname()

                print(f"\nCluster Configuration:")
                print(f"Scheduler: 1 process")
                print(f"Client: 1 process (rank 0)")
                print(f"Workers: {size - 2} processes")
                print(f"Threads per worker: {threads_per_worker or 1}")
                print(f"Memory limit per worker: {memory_limit}")
                print(f"\n{'=' * 60}")
                print(f"DASK DASHBOARD ACCESS")
                print(f"{'=' * 60}")
                print(f"Dashboard URL: {client.dashboard_link}")
                print(f"Compute Node: {hostname}")
                print(f"\nTo view the dashboard from your local machine:")
                print(f"1. Open a NEW terminal on your local machine")
                print(f"2. Run this command:")
                print(f"   ssh -L 8787:{hostname}:8787 crux.alcf.anl.gov")
                print(f"3. Open browser to: http://localhost:8787")
                print(f"\nOr use the helper script:")
                print(f"   ./scripts/tunnel_dashboard.sh {hostname}")
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
