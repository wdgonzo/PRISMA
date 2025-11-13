#!/usr/bin/env python3
"""
PRISMA Installation Verification
=================================
Verifies that PRISMA is properly installed and configured.

Checks:
- Python version (≥3.10)
- Required dependencies
- GSAS-II installation and accessibility
- XRD module imports
- Workspace directory (if configured)

Usage:
    python -m XRD.tools.verify_installation
    prisma --verify  (if installed via pip)

Author(s): William Gonzalez
Date: November 2025
Version: Beta 0.3
"""

import sys
import os
from pathlib import Path


def print_header(text):
    """Print formatted header."""
    print("\n" + "="*60)
    print(text)
    print("="*60)


def print_check(name, passed, details=""):
    """Print check result with formatted output."""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status:8} {name}")
    if details:
        print(f"         {details}")


def check_python_version():
    """Check Python version is >= 3.10."""
    version_info = sys.version_info
    version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

    if version_info >= (3, 10):
        print_check("Python version", True, f"Python {version_str}")
        return True
    else:
        print_check("Python version", False, f"Python {version_str} (requires ≥3.10)")
        return False


def check_dependencies():
    """Check required Python packages are installed."""
    print("\nChecking dependencies...")

    required_packages = [
        ('numpy', 'NumPy'),
        ('pandas', 'Pandas'),
        ('dask', 'Dask'),
        ('matplotlib', 'Matplotlib'),
        ('PyQt5', 'PyQt5'),
        ('zarr', 'Zarr'),
        ('numcodecs', 'Numcodecs'),
        ('fabio', 'FABIO'),
        ('scipy', 'SciPy'),
        ('tqdm', 'tqdm'),
    ]

    all_passed = True

    for module_name, display_name in required_packages:
        try:
            __import__(module_name)
            print_check(display_name, True)
        except ImportError as e:
            print_check(display_name, False, str(e))
            all_passed = False

    return all_passed


def check_xrd_modules():
    """Check XRD package modules can be imported."""
    print("\nChecking XRD modules...")

    modules = [
        ('XRD', 'XRD package'),
        ('XRD.core.gsas_processing', 'GSAS processing'),
        ('XRD.core.image_loader', 'Image loader'),
        ('XRD.processing.recipes', 'Recipe processing'),
        ('XRD.visualization.data_visualization', 'Data visualization'),
        ('XRD.hpc.cluster', 'HPC support'),
        ('XRD.utils.config_manager', 'Configuration manager'),
        ('XRD.utils.update_checker', 'Update checker'),
    ]

    all_passed = True

    for module_name, display_name in modules:
        try:
            __import__(module_name)
            print_check(display_name, True)
        except ImportError as e:
            print_check(display_name, False, str(e))
            all_passed = False

    return all_passed


def check_gsas():
    """Check GSAS-II installation and accessibility."""
    print("\nChecking GSAS-II...")

    # Try both import methods
    try:
        # Method 1: G2script shortcut
        import G2script
        print_check("GSAS-II (G2script)", True, "Using G2script shortcut")
        return True
    except ImportError:
        pass

    try:
        # Method 2: Direct import
        from GSASII import GSASIIscriptable as G2script
        print_check("GSAS-II (direct import)", True, "Using GSASII.GSASIIscriptable")
        return True
    except ImportError as e:
        print_check("GSAS-II", False, "Not found - requires separate installation")
        print(f"         Error: {e}")
        print("\n         GSAS-II Installation Instructions:")
        print("         1. Clone: git clone https://github.com/AdvancedPhotonSource/GSAS-II.git")
        print("         2. Configure: python XRD/initialize_gsas_headless.py /path/to/GSAS-II")
        return False


def check_workspace():
    """Check workspace configuration."""
    print("\nChecking workspace...")

    try:
        from XRD.utils.config_manager import get_config_manager
        config = get_config_manager()

        workspace_path = config.get_workspace_path()

        if workspace_path:
            if os.path.exists(workspace_path):
                print_check("Workspace configured", True, workspace_path)

                # Check subdirectories
                subdirs = ['Images', 'Processed', 'Analysis', 'recipes']
                missing_dirs = []
                for subdir in subdirs:
                    subdir_path = os.path.join(workspace_path, subdir)
                    if not os.path.exists(subdir_path):
                        missing_dirs.append(subdir)

                if missing_dirs:
                    print_check("Workspace structure", False,
                               f"Missing directories: {', '.join(missing_dirs)}")
                    return False
                else:
                    print_check("Workspace structure", True, "All directories present")
                    return True
            else:
                print_check("Workspace configured", False, f"Directory not found: {workspace_path}")
                return False
        else:
            print_check("Workspace configured", False, "Not configured (run PRISMA to set up)")
            return False

    except Exception as e:
        print_check("Workspace check", False, str(e))
        return False


def check_system_info():
    """Display system information."""
    print("\nSystem Information:")
    print(f"  Platform: {sys.platform}")
    print(f"  Python: {sys.version}")
    print(f"  Executable: {sys.executable}")

    try:
        from XRD import __version__
        print(f"  PRISMA version: {__version__}")
    except:
        print(f"  PRISMA version: Unknown (import failed)")


def main():
    """Run installation verification."""
    print_header("PRISMA Installation Verification")

    check_system_info()

    # Run all checks
    results = []

    print_header("Verification Checks")

    results.append(("Python version", check_python_version()))
    results.append(("Dependencies", check_dependencies()))
    results.append(("XRD modules", check_xrd_modules()))
    results.append(("GSAS-II", check_gsas()))
    results.append(("Workspace", check_workspace()))

    # Summary
    print_header("Summary")

    passed_count = sum(1 for name, passed in results if passed)
    total_count = len(results)

    print(f"\nPassed: {passed_count}/{total_count} checks")

    if passed_count == total_count:
        print("\n✓ Installation is valid!")
        print("\nPRISMA is ready to use. Run 'python run_prisma.py' to launch.")
        return 0
    else:
        print("\n✗ Installation has issues!")
        print("\nPlease fix the failed checks above before using PRISMA.")
        print("See docs/INSTALLATION.md for detailed setup instructions.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
