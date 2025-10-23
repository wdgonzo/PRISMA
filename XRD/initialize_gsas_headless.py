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
    Initialize GSASIIscriptable by installing the shortcut.

    Args:
        gsasii_dir: Path to GSASII subdirectory

    Returns:
        bool: True if successful, False otherwise
    """
    print("-" * 70)
    print("Installing GSASIIscriptable shortcut...")
    print("-" * 70)
    print()

    # Add GSASII directory to sys.path
    if gsasii_dir not in sys.path:
        sys.path.insert(0, gsasii_dir)

    try:
        # Import GSAS-II scriptable module
        print("Importing GSASIIscriptable...")
        from GSASII import GSASIIscriptable as G2sc

        print("✓ GSASIIscriptable imported successfully")
        print()

        # Install the scripting shortcut
        print("Installing scripting shortcut (creates G2script.py)...")
        G2sc.installScriptingShortcut()

        print()
        print("✓ GSASIIscriptable shortcut installed successfully!")
        print()

        return True

    except ImportError as e:
        print(f"✗ Failed to import GSASIIscriptable: {e}")
        print()
        print("This usually means:")
        print("  1. GSAS-II is not properly installed")
        print("  2. Required Python packages are missing")
        print("  3. Binary files are not compiled")
        print()
        return False

    except Exception as e:
        print(f"✗ Error during installation: {e}")
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
    gsas_base = os.path.dirname(gsasii_dir)

    print("=" * 70)
    print("GSAS-II Environment Setup")
    print("=" * 70)
    print()
    print("Add these lines to your ~/.bashrc or environment activation script:")
    print()
    print(f"    export GSAS2DIR={gsas_base}/GSASII")
    print(f"    export PYTHONPATH=${{GSAS2DIR}}:${{PYTHONPATH}}")
    print()
    print("To apply immediately:")
    print()
    print(f"    export GSAS2DIR={gsas_base}/GSASII")
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

    try:
        import G2script as G2sc
        print("✓ G2script imported successfully!")
        print(f"  Location: {G2sc.__file__}")
        print()

        # Try to show versions
        try:
            G2sc.ShowVersions()
        except:
            pass  # ShowVersions might print, which is fine

        return True

    except ImportError as e:
        print(f"✗ Failed to import G2script: {e}")
        print()
        print("This is expected if you haven't sourced your environment yet.")
        print("After adding GSAS2DIR to your environment and sourcing ~/.bashrc,")
        print("you should be able to import G2script.")
        print()
        return False


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
        print("INITIALIZATION FAILED")
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
    print("INITIALIZATION COMPLETE")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Add environment variables to your ~/.bashrc (see above)")
    print("  2. Source your bashrc: source ~/.bashrc")
    print("  3. Test import: python -c 'import G2script; print(G2script.__file__)'")
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
