"""
HPC module - High-performance computing cluster support
=======================================================

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

from XRD.hpc.cluster import (
    get_dask_client,
    close_dask_client,
    is_mpi_environment,
    configure_hpc_environment
)

__all__ = [
    'get_dask_client',
    'close_dask_client',
    'is_mpi_environment',
    'configure_hpc_environment',
]
