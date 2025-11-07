#!/usr/bin/env python3
"""
Batch Recipe Processor for XRD Data Generation
===============================================
This script processes all recipe JSON files in the recipes/ directory sequentially.
Each recipe generates a single XRD dataset with specified peak configurations.

Usage:
    python batch_processor.py                    # Process all recipes
    python batch_processor.py --create-examples  # Create example recipes
    python batch_processor.py recipe_name.json   # Process single recipe

The script looks for JSON files in the recipes/ directory and generates Zarr data.
Use data_analyzer.py to visualize and analyze the generated data.

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import os
import json
import shutil
import time
from datetime import datetime
import glob
import sys

# Import the data generation module
from XRD.processing import data_generator
from XRD.processing.recipes import load_recipe_from_file


def process_all_recipes(home_dir: str = None, client=None, benchmark_file=None, move_recipes: bool = True):
    """
    Process all recipe files in the recipes directory.

    Args:
        home_dir: Optional home directory. If None, uses current directory.
        client: Optional Dask client to reuse across recipes (for HPC efficiency)
        benchmark_file: Optional path to benchmark CSV file for incremental writing
        move_recipes: If True, move recipes to processed/ after success (default: True)

    Returns:
        List of dictionaries containing benchmark metrics for each recipe
    """
    from XRD.utils.path_manager import get_recipes_path, get_processed_recipes_path

    # Default to current directory if not specified
    if home_dir is None:
        home_dir = os.getcwd()

    recipe_dir = get_recipes_path(home_dir)
    processed_dir = get_processed_recipes_path(home_dir)

    # Create processed directory if it doesn't exist
    os.makedirs(processed_dir, exist_ok=True)

    # Find all JSON files in the recipe directory
    recipe_files = glob.glob(os.path.join(recipe_dir, "*.json"))

    if not recipe_files:
        print(f"No recipe files found in {recipe_dir}/")
        print("   Use recipe_builder.py to create recipes")
        print("   Or use --create-examples to generate sample recipes")
        return []

    print(f"Found {len(recipe_files)} recipe files")
    print("=" * 60)
    print(f"DEBUG: process_all_recipes() ENTERED")
    print(f"DEBUG: client = {client}")
    print(f"DEBUG: benchmark_file = {benchmark_file}")

    success_count = 0
    error_count = 0
    benchmark_metrics = []  # Collect benchmark data for each recipe

    print(f"DEBUG: About to loop through {len(recipe_files)} recipes")
    for recipe_file in recipe_files:
        print(f"DEBUG: Loop iteration - recipe_file = {recipe_file}")
        recipe_name = os.path.basename(recipe_file)
        print(f"\nProcessing: {recipe_name}")

        try:
            # Load recipe
            recipe_data = load_recipe_from_file(recipe_file)

            print(f"   Sample: {recipe_data.get('sample', 'Unknown')}")
            print(f"   Setting: {recipe_data.get('setting', 'Unknown')}")
            print(f"   Stage: {recipe_data.get('stage', 'Unknown')}")
            print(f"   Peaks: {len(recipe_data.get('active_peaks', []))}")

            # Process the recipe (pass client to reuse across recipes)
            print(f"DEBUG: About to call generate_data_from_recipe()")
            start_time = time.time()
            dataset = data_generator.generate_data_from_recipe(recipe_data, recipe_name, client)
            print(f"DEBUG: generate_data_from_recipe() returned")
            processing_time = time.time() - start_time

            if dataset:
                print(f"   Success! Generated dataset in {processing_time:.1f}s")
                print(f"   Shape: {dataset.data.shape}")

                # Collect benchmark metrics
                num_frames = dataset.data.shape[1]  # frames dimension
                num_peaks = dataset.data.shape[0]   # peaks dimension
                num_azimuths = dataset.data.shape[2]  # azimuths dimension

                metric = {
                    'recipe_name': recipe_name,
                    'sample': recipe_data.get('sample', 'Unknown'),
                    'stage': recipe_data.get('stage', 'Unknown'),
                    'num_frames': num_frames,
                    'num_peaks': num_peaks,
                    'num_azimuths': num_azimuths,
                    'processing_time_sec': round(processing_time, 1),
                    'status': 'SUCCESS'
                }
                benchmark_metrics.append(metric)

                # Write to benchmark file immediately (incremental, prevents data loss)
                if benchmark_file:
                    write_benchmark_entry(benchmark_file, metric)

                # Verify save path exists
                save_path = dataset.params.save_path()
                if os.path.exists(save_path):
                    print(f"   Zarr file verified: {os.path.basename(save_path)}")
                else:
                    print(f"   WARNING: Zarr file not found at expected location!")
                    print(f"      Expected: {save_path}")

                # Move processed file to processed directory (if enabled)
                if move_recipes:
                    processed_file = os.path.join(processed_dir, recipe_name)
                    shutil.move(recipe_file, processed_file)
                    print(f"   Moved recipe to processed/")
                else:
                    print(f"   Recipe kept in place (--no-move active)")

                success_count += 1
            else:
                print(f"   Dataset generation failed")

                # Record failed recipe in benchmarks
                metric = {
                    'recipe_name': recipe_name,
                    'sample': recipe_data.get('sample', 'Unknown'),
                    'stage': recipe_data.get('stage', 'Unknown'),
                    'num_frames': 0,
                    'num_peaks': 0,
                    'num_azimuths': 0,
                    'processing_time_sec': round(processing_time, 1),
                    'status': 'FAILED'
                }
                benchmark_metrics.append(metric)

                # Write to benchmark file immediately
                if benchmark_file:
                    write_benchmark_entry(benchmark_file, metric)

                error_count += 1

        except Exception as e:
            print(f"   Error: {str(e)}")

            # Record exception in benchmarks
            metric = {
                'recipe_name': recipe_name,
                'sample': 'ERROR',
                'stage': 'ERROR',
                'num_frames': 0,
                'num_peaks': 0,
                'num_azimuths': 0,
                'processing_time_sec': 0.0,
                'status': 'ERROR'
            }
            benchmark_metrics.append(metric)

            # Write to benchmark file immediately
            if benchmark_file:
                write_benchmark_entry(benchmark_file, metric)

            error_count += 1
            continue

    # Summary
    print("\n" + "=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print(f"   Successful: {success_count}")
    print(f"   Failed: {error_count}")
    print(f"   Total: {len(recipe_files)}")

    return benchmark_metrics


def create_example_recipes():
    """
    Create example recipe files for batch processing.
    """
    recipe_dir = "recipes"
    os.makedirs(recipe_dir, exist_ok=True)

    examples = [
        {
            "name": "A1_Standard_CONT_211",
            "recipe": {
                "sample": "A1",
                "setting": "Standard",
                "stage": "CONT",
                "image_folder": "/path/to/images",
                "control_file": "/path/to/control.imctrl",
                "mask_file": "/path/to/mask.immask",
                "exposure": "019",
                "step": 1,
                "spacing": 5,
                "frame_start": 0,
                "frame_end": 100,
                "az_start": -110,
                "az_end": 110,
                "active_peaks": [
                    {
                        "name": "Martensite 211",
                        "miller_index": "211",
                        "position": 8.46,
                        "limits": [8.2, 8.8]
                    }
                ],
                "notes": "Example A1 single peak"
            }
        },
        {
            "name": "B2_Speed_CONT_MultiPeak",
            "recipe": {
                "sample": "B2",
                "setting": "Speed",
                "stage": "CONT",
                "image_folder": "/path/to/images",
                "control_file": "/path/to/control.imctrl",
                "mask_file": "/path/to/mask.immask",
                "exposure": "009",
                "step": 1,
                "spacing": 10,
                "frame_start": 500,
                "frame_end": 600,
                "az_start": -90,
                "az_end": 90,
                "active_peaks": [
                    {
                        "name": "Martensite 211",
                        "miller_index": "211",
                        "position": 8.46,
                        "limits": [8.2, 8.8]
                    },
                    {
                        "name": "Austenite 110",
                        "miller_index": "110",
                        "position": 7.32,
                        "limits": [7.1, 7.5]
                    }
                ],
                "notes": "Example B2 multi-peak analysis"
            }
        }
    ]

    print("Creating example recipes...")

    for example in examples:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{example['name']}_{timestamp}.json"
        filepath = os.path.join(recipe_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(example['recipe'], f, indent=4)

        print(f"   Created: {filename}")

    print(f"\nExample recipes saved to {recipe_dir}/")
    print("   Edit these files with your actual paths and parameters")
    print("   Or use recipe_builder.py to create new recipes")
    print("   Then run: python batch_processor.py")


def process_single_recipe(recipe_name: str, home_dir: str = None):
    """
    Process a single recipe file.

    Args:
        recipe_name: Name of the recipe file to process
        home_dir: Optional home directory
    """
    from XRD.utils.path_manager import get_recipes_path

    if home_dir is None:
        home_dir = os.getcwd()

    recipe_dir = get_recipes_path(home_dir)
    recipe_path = os.path.join(recipe_dir, recipe_name)

    # Also try current directory as fallback
    if not os.path.exists(recipe_path):
        recipe_path = os.path.join("recipes", recipe_name)

    if not os.path.exists(recipe_path):
        print(f"Recipe file not found: {recipe_name}")
        print(f"   Searched in: {get_recipes_path(home_dir)}")
        print(f"   And: recipes/")
        return False

    print(f"Processing single recipe: {recipe_name}")
    print("=" * 60)

    try:
        # Load and process recipe
        recipe_data = load_recipe_from_file(recipe_path)

        print(f"   Sample: {recipe_data.get('sample', 'Unknown')}")
        print(f"   Setting: {recipe_data.get('setting', 'Unknown')}")
        print(f"   Stage: {recipe_data.get('stage', 'Unknown')}")
        print(f"   Peaks: {len(recipe_data.get('active_peaks', []))}")

        start_time = time.time()
        dataset = data_generator.generate_data_from_recipe(recipe_data, recipe_name)
        processing_time = time.time() - start_time

        if dataset:
            print(f"\nSuccess! Generated dataset in {processing_time:.1f}s")
            print(f"   Shape: {dataset.data.shape}")
            save_path = dataset.params.save_path()
            print(f"   Zarr file: {save_path}")

            # Verify the save was successful
            if os.path.exists(save_path):
                print(f"   Dataset successfully saved and verified")
            else:
                print(f"   WARNING: Dataset save verification failed!")
                print(f"      Path does not exist: {save_path}")

            return True
        else:
            print(f"\nDataset generation failed")
            return False

    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def initialize_benchmark_file(home_dir, num_workers, num_nodes, workers_per_node):
    """
    Initialize benchmark CSV file with headers.

    Args:
        home_dir: Base directory for output
        num_workers: Number of Dask workers
        num_nodes: Number of MPI nodes
        workers_per_node: Workers per node configuration

    Returns:
        Path to the benchmark file
    """
    # Create benchmarks directory
    benchmark_dir = os.path.join(home_dir, "Params", "benchmarks")
    os.makedirs(benchmark_dir, exist_ok=True)

    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    benchmark_file = os.path.join(benchmark_dir, f"batch_benchmark_{timestamp}.csv")

    # Write header
    with open(benchmark_file, 'w') as f:
        f.write(f"# Batch Benchmark - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Workers: {num_workers}, Nodes: {num_nodes}, Workers/Node: {workers_per_node}\n")
        f.write("#\n")
        f.write("Recipe,Sample,Stage,Frames,Peaks,Azimuths,Time_sec,Status\n")

    return benchmark_file


def write_benchmark_entry(benchmark_file, metric):
    """
    Append a single benchmark entry to the CSV file.

    Args:
        benchmark_file: Path to the benchmark CSV file
        metric: Dictionary containing benchmark metrics for one recipe
    """
    with open(benchmark_file, 'a') as f:
        f.write(f"{metric['recipe_name']},{metric['sample']},{metric['stage']},"
               f"{metric['num_frames']},{metric['num_peaks']},{metric['num_azimuths']},"
               f"{metric['processing_time_sec']},{metric['status']}\n")


def finalize_benchmark_file(benchmark_file, benchmark_metrics, total_time):
    """
    Append summary statistics to the benchmark file.

    Args:
        benchmark_file: Path to the benchmark CSV file
        benchmark_metrics: List of all benchmark metrics
        total_time: Total batch processing time in seconds
    """
    total_frames = 0
    total_successful_time = 0
    for metric in benchmark_metrics:
        if metric['status'] == 'SUCCESS':
            total_frames += metric['num_frames']
            total_successful_time += metric['processing_time_sec']

    with open(benchmark_file, 'a') as f:
        f.write("#\n")
        f.write(f"# Batch completed in {total_time:.1f} seconds ({total_time/60:.1f} minutes)\n")
        f.write(f"# Summary: {len([m for m in benchmark_metrics if m['status'] == 'SUCCESS'])} successful recipes\n")
        f.write(f"# Total frames processed: {total_frames}\n")
        f.write(f"# Average time per recipe: {total_successful_time / max(1, len(benchmark_metrics)):.1f} seconds\n")
        if total_frames > 0:
            f.write(f"# Average time per frame: {total_successful_time / total_frames:.2f} seconds\n")


def get_cluster_info():
    """
    Get information about the Dask cluster (workers, nodes).

    Returns:
        Tuple of (num_workers, num_nodes, workers_per_node)
    """
    from XRD.hpc.cluster import is_mpi_environment

    num_workers = 1  # Default for non-Dask execution
    num_nodes = 1
    workers_per_node = 1

    try:
        # Try to get Dask client if it exists
        from distributed import get_client
        try:
            client = get_client()
            scheduler_info = client.scheduler_info()
            num_workers = len(scheduler_info['workers'])

            # Check if running in MPI environment
            if is_mpi_environment():
                try:
                    from mpi4py import MPI
                    comm = MPI.COMM_WORLD
                    num_nodes = comm.Get_size()

                    # Try to get workers per node from environment
                    workers_per_node = int(os.environ.get('WORKERS_PER_NODE', num_workers // max(1, num_nodes)))
                except ImportError:
                    # Fallback: estimate from worker count
                    num_nodes = max(1, num_workers // 2)  # Rough estimate
                    workers_per_node = num_workers // num_nodes
            else:
                # Local cluster - single node
                num_nodes = 1
                workers_per_node = num_workers

        except ValueError:
            # No client available - not using Dask
            pass
    except ImportError:
        # Dask not available
        pass

    return num_workers, num_nodes, workers_per_node


def main():
    """
    Main function to handle command line arguments and execute batch processing.
    """
    home_dir = os.getcwd()  # Default to current directory
    move_recipes = True  # Default: move recipes to processed/ after success

    # Parse command line arguments
    if len(sys.argv) > 1:
        # Check for --no-move flag anywhere in arguments
        if "--no-move" in sys.argv:
            move_recipes = False
            # Remove --no-move from argv for other parsing
            sys.argv = [arg for arg in sys.argv if arg != "--no-move"]

        if sys.argv[1] == "--create-examples":
            create_example_recipes()
            return
        elif sys.argv[1] == "--home" and len(sys.argv) > 2:
            # Set home directory
            home_dir = sys.argv[2]
            print(f"Using home directory: {home_dir}")
            if len(sys.argv) > 3 and sys.argv[3].endswith(".json"):
                # Process single recipe with custom home
                success = process_single_recipe(sys.argv[3], home_dir)
                if success:
                    print("\nRecipe processing completed successfully!")
                    print("Use data_analyzer.py to visualize the generated data")
                else:
                    print("\nRecipe processing failed")
                return
        elif sys.argv[1].endswith(".json"):
            # Process single recipe
            success = process_single_recipe(sys.argv[1], home_dir)
            if success:
                print("\nRecipe processing completed successfully!")
                print("Use data_analyzer.py to visualize the generated data")
            else:
                print("\nRecipe processing failed")
            return

    # Default: process all recipes
    print("XRD BATCH RECIPE PROCESSOR v3.0")
    print("=" * 60)
    print(f"Home directory: {home_dir}")
    print("Processing all recipes for data generation...")
    print()

    # Import cluster management
    from XRD.hpc.cluster import get_dask_client, close_dask_client

    # Create Dask client ONCE before processing (critical for HPC/MPI mode)
    print("Initializing Dask cluster...")
    client = get_dask_client()

    # Gather worker/core information before processing
    num_workers, num_nodes, workers_per_node = get_cluster_info()
    print(f"Cluster initialized: {num_workers} workers, {num_nodes} nodes")
    print()

    # Initialize benchmark file with headers
    benchmark_file = initialize_benchmark_file(home_dir, num_workers, num_nodes, workers_per_node)
    print(f"Benchmark file: {benchmark_file}")
    print()

    # Warning if recipes will not be moved
    if not move_recipes:
        print("WARNING: --no-move flag is active")
        print("   Recipes will NOT be moved to processed/ after completion")
        print("   This may cause reprocessing if the batch is run again")
        print("   Consider manually removing or archiving processed recipes")
        print()

    try:
        # Start batch processing (client reused across all recipes)
        print("DEBUG: About to call process_all_recipes()")
        print(f"DEBUG: client = {client}")
        print(f"DEBUG: benchmark_file = {benchmark_file}")
        start_time = time.time()
        benchmark_metrics = process_all_recipes(home_dir, client, benchmark_file, move_recipes)
        print(f"DEBUG: process_all_recipes() returned, got {len(benchmark_metrics)} metrics")
        total_time = time.time() - start_time

        print(f"\nBatch processing completed in {total_time:.1f} seconds")

        # Finalize benchmark file with summary statistics
        if benchmark_metrics:
            finalize_benchmark_file(benchmark_file, benchmark_metrics, total_time)
            print(f"\nBenchmark results saved to:")
            print(f"   {benchmark_file}")

        print("Use data_analyzer.py to visualize generated data")

    finally:
        # Always close the client, even if processing fails
        print("\nClosing Dask cluster...")
        close_dask_client(client)


if __name__ == "__main__":
    main()