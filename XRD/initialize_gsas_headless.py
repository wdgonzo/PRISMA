#!/usr/bin/env python3
"""
Headless GSAS-II Initialization
================================
Command-line initialization of GSASIIscriptable for HPC/server environments.

This script replaces the GUI-based initialization in initialize.py with
a command-line interface suitable for SSH/terminal use on supercomputers.

Functionality:
- Prompts for GSAS-II installation directory path
- Validates GSAS-II installation
- Calls installScriptingShortcut() programmatically
- Creates G2script shortcut for easy importing
- No GUI dependencies (works headless)

Usage:
    python XRD/initialize_gsas_headless.py [gsas_dir]

    If gsas_dir is not provided, will prompt interactively.

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import sys
import os
import os.path


def validate_gsas_directory(gsas_dir):
    """
    Validate that the given directory is a valid GSAS-II installation.

    Args:
        gsas_dir: Path to potential GSAS-II directory

    Returns:
        tuple: (is_valid, gsasii_subdir, error_message)
    """
    if not os.path.exists(gsas_dir):
        return False, None, f"Directory does not exist: {gsas_dir}"

    if not os.path.isdir(gsas_dir):
        return False, None, f"Not a directory: {gsas_dir}"

    # Check for GSASII subdirectory
    gsasii_dir = os.path.join(gsas_dir, 'GSASII')
    if not os.path.isdir(gsasii_dir):
        return False, None, f"GSASII subdirectory not found in {gsas_dir}"

    # Check for key GSAS-II files
    required_files = [
        'GSASIIscriptable.py',
        'GSASIIpath.py',
        'GSASIIfiles.py'
    ]

    missing_files = []
    for filename in required_files:
        filepath = os.path.join(gsasii_dir, filename)
        if not os.path.exists(filepath):
            missing_files.append(filename)

    if missing_files:
        return False, None, f"Missing required files in {gsasii_dir}: {', '.join(missing_files)}"

    # Check for compiled binaries (optional but recommended)
    # GSAS-II expects binaries at GSAS-II/GSASII-bin/ (repository root), not GSASII/bin/
    gsas_root = os.path.dirname(gsasii_dir)
    bin_dir = os.path.join(gsas_root, 'GSASII-bin')

    if os.path.isdir(bin_dir):
        # Look for any platform-specific binary directories
        bin_subdirs = [d for d in os.listdir(bin_dir) if os.path.isdir(os.path.join(bin_dir, d))]
        if bin_subdirs:
            print(f"  ℹ Found compiled binaries in GSASII-bin/: {', '.join(bin_subdirs)}")
        else:
            print(f"  ⚠ Warning: GSASII-bin/ exists but no compiled binaries found")
            print(f"    You may need to compile GSAS-II for your platform")
    else:
        print(f"  ⚠ Warning: No GSASII-bin/ directory found - GSAS-II may not be compiled")
        print(f"    Run: bash scripts/compile_gsas_crux.sh {gsas_dir}")

    return True, gsasii_dir, None


def get_gsas_directory_interactive():
    """
    Interactively prompt user for GSAS-II directory.

    Returns:
        str: Valid GSASII directory path
    """
    print("=" * 70)
    print("GSAS-II Headless Initialization")
    print("=" * 70)
    print()
    print("This script will set up GSASIIscriptable for command-line use.")
    print()

    # Suggest common locations
    common_locations = [
        os.path.expanduser("~/GSAS-II"),
        os.path.expanduser("~/Software/GSAS-II"),
        "/eagle/APS_INSITU_STUDY_APP/Software/GSAS-II",
        "../GSAS-II",
    ]

    print("Common GSAS-II installation locations:")
    for i, loc in enumerate(common_locations, 1):
        expanded = os.path.expanduser(loc)
        exists_marker = "✓" if os.path.exists(expanded) else " "
        print(f"  [{i}] {exists_marker} {loc}")

    print()

    while True:
        print("Enter GSAS-II installation directory path:")
        print("  (or enter a number 1-{} to use a common location)".format(len(common_locations)))
        user_input = input("> ").strip()

        if not user_input:
            print("  ERROR: No path provided. Please try again.\n")
            continue

        # Check if user entered a number
        if user_input.isdigit():
            choice = int(user_input)
            if 1 <= choice <= len(common_locations):
                gsas_dir = os.path.expanduser(common_locations[choice - 1])
                print(f"  Selected: {gsas_dir}")
            else:
                print(f"  ERROR: Invalid choice. Please enter 1-{len(common_locations)} or a path.\n")
                continue
        else:
            gsas_dir = os.path.expanduser(user_input)

        # Validate directory
        is_valid, gsasii_dir, error_msg = validate_gsas_directory(gsas_dir)

        if is_valid:
            print(f"\n✓ Valid GSAS-II installation found: {gsasii_dir}\n")
            return gsasii_dir
        else:
            print(f"\n✗ Invalid GSAS-II directory: {error_msg}\n")
            print("Please try again or press Ctrl+C to exit.\n")


def initialize_gsas_scriptable(gsasii_dir):
    """
    Validate GSAS-II setup for headless/HPC environments.
    For Option 2 approach: direct imports via PYTHONPATH (no G2script shortcut needed).

    Args:
        gsasii_dir: Path to GSASII subdirectory

    Returns:
        bool: True if setup is valid, False otherwise
    """
    print("-" * 70)
    print("Validating GSAS-II setup for headless/HPC use...")
    print("-" * 70)
    print()

    gsas_root = os.path.dirname(gsasii_dir)

    print("✓ GSAS-II files validated")
    print(f"  GSAS-II root: {gsas_root}")
    print(f"  GSASII package: {gsasii_dir}")
    print()

    # Test direct import (Option 2 approach)
    print("Testing direct import (Option 2 - no G2script shortcut needed)...")
    print(f"  Adding {gsas_root} to sys.path")

    if gsas_root not in sys.path:
        sys.path.insert(0, gsas_root)

    # Set GSAS2DIR to root directory (matches official docs)
    os.environ['GSAS2DIR'] = gsas_root

    try:
        print("  Importing GSASII.GSASIIscriptable...")
        from GSASII import GSASIIscriptable as G2sc

        print("  ✓ Direct import successful!")
        print()

        # Install G2script shortcut (run once per venv - official method from docs)
        print("Installing G2script shortcut (creates G2script.py in site-packages)...")
        print("  This only needs to be done once per virtual environment.")
        try:
            G2sc.installScriptingShortcut()
            print("  ✓ G2script shortcut installed successfully!")
            print()
            print("✓ GSAS-II is ready for use")
            print()
            print("You can now use:")
            print("  import G2script")
            print()
            print("in any Python script without modifying sys.path")
        except Exception as e:
            print(f"  ⚠ Shortcut installation warning: {e}")
            print()
            print("  Shortcut installation failed, but direct import still works:")
            print("  from GSASII import GSASIIscriptable as G2script")
            print()
            print("  Make sure PYTHONPATH includes GSAS-II root:")
            print(f"  export PYTHONPATH={gsas_root}:$PYTHONPATH")
        print()

        return True

    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Verify GSAS-II is properly installed")
        print("  2. Check that binaries are compiled (see GSASII-bin/)")
        print("  3. Ensure PYTHONPATH includes GSAS-II root directory")
        print()
        print("Debug information:")
        print(f"  GSAS-II root: {gsas_root}")
        print(f"  GSASII package: {gsasii_dir}")
        print(f"  GSASIIpath.py exists: {os.path.exists(os.path.join(gsasii_dir, 'GSASIIpath.py'))}")
        print(f"  GSASIIscriptable.py exists: {os.path.exists(os.path.join(gsasii_dir, 'GSASIIscriptable.py'))}")
        print()
        return False

    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


def create_environment_info(gsasii_dir):
    """
    Create instructions for setting up environment variables.

    Args:
        gsasii_dir: Path to GSASII subdirectory
    """
    gsas_root = os.path.dirname(gsasii_dir)

    print("=" * 70)
    print("GSAS-II Environment Setup")
    print("=" * 70)
    print()
    print("Add these lines to your ~/.bashrc or environment activation script:")
    print()
    print(f"    export GSAS2DIR={gsas_root}")
    print(f"    export PYTHONPATH=${{GSAS2DIR}}:${{PYTHONPATH}}")
    print()
    print("To apply immediately:")
    print()
    print(f"    export GSAS2DIR={gsas_root}")
    print(f"    export PYTHONPATH=${{GSAS2DIR}}:${{PYTHONPATH}}")
    print()


def test_import():
    """
    Test that G2script can be imported.

    Returns:
        bool: True if import successful
    """
    print("-" * 70)
    print("Testing G2script import...")
    print("-" * 70)
    print()

    # Test both import methods (Option 1: G2script shortcut, Option 2: direct import)
    print("Testing import methods...")
    print()

    # Try G2script shortcut first (if installed via GUI)
    try:
        import G2script as G2sc
        print("✓ G2script shortcut available (GUI-installed)")
        print(f"  Location: {G2sc.__file__}")
        method = "G2script shortcut"
    except ImportError:
        # Try direct import (Option 2)
        try:
            from GSASII import GSASIIscriptable as G2sc
            print("✓ Direct import successful (headless/HPC mode)")
            print(f"  Location: {G2sc.__file__}")
            method = "Direct import"
        except ImportError as e:
            print(f"✗ Both import methods failed: {e}")
            print()
            print("Make sure PYTHONPATH includes GSAS-II root directory:")
            print("  export PYTHONPATH=/path/to/GSAS-II:$PYTHONPATH")
            print()
            return False

    print(f"  Using: {method}")
    print()

    # Try to show versions
    try:
        G2sc.ShowVersions()
    except:
        pass  # ShowVersions might print, which is fine

    return True


def main():
    """Main execution function."""
    # Check if GSAS directory was provided as command-line argument
    if len(sys.argv) > 1:
        gsas_dir = os.path.expanduser(sys.argv[1])
        is_valid, gsasii_dir, error_msg = validate_gsas_directory(gsas_dir)

        if not is_valid:
            print(f"ERROR: {error_msg}")
            print()
            print("Please provide a valid GSAS-II installation directory.")
            print("Usage: python initialize_gsas_headless.py [gsas_dir]")
            sys.exit(1)
    else:
        # Interactive mode
        gsasii_dir = get_gsas_directory_interactive()

    # Initialize GSAS-II scriptable
    success = initialize_gsas_scriptable(gsasii_dir)

    if not success:
        print("=" * 70)
        print("VALIDATION FAILED")
        print("=" * 70)
        print()
        print("Please check the error messages above and try again.")
        print()
        sys.exit(1)

    # Provide environment setup instructions
    create_environment_info(gsasii_dir)

    # Test import
    test_import()

    print("=" * 70)
    print("GSAS-II SETUP COMPLETE (Option 2: Direct Import)")
    print("=" * 70)
    print()
    print("Your code is configured to import GSAS-II directly (no shortcut needed):")
    print("  - Works on both local and HPC systems")
    print("  - Tries G2script shortcut first (if GUI-installed)")
    print("  - Falls back to direct import for headless environments")
    print()
    print("Next steps:")
    print("  1. Source your environment: source activate_xrd.sh")
    print("  2. Test import: python -c 'from GSASII import GSASIIscriptable; print(\"OK\")'")
    print("  3. Run your processing code as normal")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
