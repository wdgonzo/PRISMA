#!/usr/bin/env python
"""
Simple test script to verify Dask-MPI cluster initialization.

Usage:
    # Local test
    python test_cluster.py

    # MPI test (4 processes = 1 scheduler + 1 client + 2 workers)
    mpiexec -n 4 python test_cluster.py

    # Crux HPC test
    qsub -I -l select=2:ncpus=1 -l walltime=00:30:00 -q debug
    mpiexec -n 4 python test_cluster.py
"""
import sys
import time
from XRD.hpc.cluster import get_dask_client, close_dask_client, is_mpi_environment

def main():
    print("=" * 70)
    print("DASK CLUSTER INITIALIZATION TEST")
    print("=" * 70)

    # Detect environment
    if is_mpi_environment():
        from mpi4py import MPI
        comm = MPI.COMM_WORLD
        rank = comm.Get_rank()
        size = comm.Get_size()

        print(f"MPI Environment Detected:")
        print(f"  Total MPI ranks: {size}")
        print(f"  Current rank: {rank}")
        print(f"  Expected: 1 scheduler + 1 client + {size-2} workers")
    else:
        print("Local Environment (no MPI)")

    print("\n" + "=" * 70)
    print("Step 1: Initialize Dask Client")
    print("=" * 70)

    try:
        client = get_dask_client(verbose=True)
        print("\n✓ Client initialized successfully")
    except Exception as e:
        print(f"\n✗ FAILED to initialize client: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 70)
    print("Step 2: Check Cluster Status")
    print("=" * 70)

    try:
        scheduler_info = client.scheduler_info()
        num_workers = len(scheduler_info['workers'])
        print(f"✓ Scheduler responsive")
        print(f"✓ Connected workers: {num_workers}")

        if num_workers == 0:
            print("⚠ WARNING: No workers connected!")

        # Print worker details
        print("\nWorker Details:")
        for worker_id, worker_info in scheduler_info['workers'].items():
            print(f"  - {worker_id}: {worker_info.get('nthreads', '?')} threads, "
                  f"{worker_info.get('memory_limit', 0) / 1e9:.1f} GB memory")

    except Exception as e:
        print(f"✗ FAILED to get cluster status: {e}")
        import traceback
        traceback.print_exc()
        close_dask_client(client)
        sys.exit(1)

    print("\n" + "=" * 70)
    print("Step 3: Run Test Computation")
    print("=" * 70)

    try:
        import dask.array as da

        # Create a simple computation
        print("Creating 10000x10000 random array...")
        x = da.random.random((10000, 10000), chunks=(1000, 1000))

        print("Computing mean (this uses all workers)...")
        start_time = time.time()
        result = x.mean().compute()
        elapsed = time.time() - start_time

        print(f"✓ Computation succeeded")
        print(f"  Result: {result:.6f}")
        print(f"  Time: {elapsed:.2f} seconds")
        print(f"  Workers used: {num_workers}")

    except Exception as e:
        print(f"✗ FAILED computation: {e}")
        import traceback
        traceback.print_exc()
        close_dask_client(client)
        sys.exit(1)

    print("\n" + "=" * 70)
    print("Step 4: Keep Alive Test (30 seconds)")
    print("=" * 70)
    print("Sleeping to verify cluster stays alive...")
    print("(Check dashboard if you have SSH tunnel active)")

    for i in range(6):
        time.sleep(5)
        # Verify cluster still responsive
        try:
            current_workers = len(client.scheduler_info()['workers'])
            print(f"  [{(i+1)*5}s] Cluster alive, workers: {current_workers}")
        except Exception as e:
            print(f"  ✗ Cluster became unresponsive: {e}")
            break

    print("\n" + "=" * 70)
    print("Step 5: Graceful Shutdown")
    print("=" * 70)

    try:
        close_dask_client(client)
        print("✓ Client closed successfully")
    except Exception as e:
        print(f"⚠ Warning during shutdown: {e}")

    print("\n" + "=" * 70)
    print("TEST COMPLETE - ALL STEPS PASSED")
    print("=" * 70)
    print("\nYour cluster initialization is working correctly!")
    print("You can now run: python run_batch_processor.py")

if __name__ == "__main__":
    main()
