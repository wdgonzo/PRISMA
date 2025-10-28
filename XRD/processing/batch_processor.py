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


def process_all_recipes(home_dir: str = None):
    """
    Process all recipe files in the recipes directory.

    Args:
        home_dir: Optional home directory. If None, uses current directory.
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
        return

    print(f"Found {len(recipe_files)} recipe files")
    print("=" * 60)

    success_count = 0
    error_count = 0

    for recipe_file in recipe_files:
        recipe_name = os.path.basename(recipe_file)
        print(f"\nProcessing: {recipe_name}")

        try:
            # Load recipe
            recipe_data = load_recipe_from_file(recipe_file)

            print(f"   Sample: {recipe_data.get('sample', 'Unknown')}")
            print(f"   Setting: {recipe_data.get('setting', 'Unknown')}")
            print(f"   Stage: {recipe_data.get('stage', 'Unknown')}")
            print(f"   Peaks: {len(recipe_data.get('active_peaks', []))}")

            # Process the recipe
            start_time = time.time()
            dataset = data_generator.generate_data_from_recipe(recipe_data, recipe_name)
            processing_time = time.time() - start_time

            if dataset:
                print(f"   Success! Generated dataset in {processing_time:.1f}s")
                print(f"   Shape: {dataset.data.shape}")

                # Verify save path exists
                save_path = dataset.params.save_path()
                if os.path.exists(save_path):
                    print(f"   Zarr file verified: {os.path.basename(save_path)}")
                else:
                    print(f"   WARNING: Zarr file not found at expected location!")
                    print(f"      Expected: {save_path}")

                # Move processed file to processed directory
                processed_file = os.path.join(processed_dir, recipe_name)
                shutil.move(recipe_file, processed_file)
                print(f"   Moved recipe to processed/")

                success_count += 1
            else:
                print(f"   Dataset generation failed")
                error_count += 1

        except Exception as e:
            print(f"   Error: {str(e)}")
            error_count += 1
            continue

    # Summary
    print("\n" + "=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print(f"   Successful: {success_count}")
    print(f"   Failed: {error_count}")
    print(f"   Total: {len(recipe_files)}")


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


def main():
    """
    Main function to handle command line arguments and execute batch processing.
    """
    home_dir = os.getcwd()  # Default to current directory

    # Parse command line arguments
    if len(sys.argv) > 1:
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

    # Start batch processing
    start_time = time.time()
    process_all_recipes(home_dir)
    total_time = time.time() - start_time

    print(f"\nBatch processing completed in {total_time:.1f} seconds")
    print("Use data_analyzer.py to visualize generated data")


if __name__ == "__main__":
    main()