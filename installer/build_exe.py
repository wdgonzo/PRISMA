#!/usr/bin/env python3
"""
PRISMA Executable Builder
==========================
Builds standalone PRISMA.exe using PyInstaller.

Usage:
    python build_exe.py [--clean]

Output:
    dist/PRISMA.exe - Standalone executable

Requirements:
    - PyInstaller: pip install pyinstaller
    - Pillow (for icon generation): pip install Pillow

Author: William Gonzalez
Date: November 2025
Version: Beta 0.3
"""

import sys
import os
import subprocess
import shutil
import argparse
from pathlib import Path


def check_and_install_dependencies():
    """
    Check for required dependencies and install missing ones.

    This ensures PyInstaller can bundle all required packages.
    Returns True if all dependencies are available.
    """
    print("\nChecking build dependencies...")

    # Required packages for building PRISMA
    required_packages = [
        "numpy>=2.0,<3.0",
        "pandas",
        "dask[distributed]",
        "dask-mpi",
        "mpi4py",
        "matplotlib",
        "seaborn",
        "imageio",
        "tqdm",
        "scipy",
        "pyqt5",
        "openpyxl",
        "pybaselines",
        "bokeh",
        "zarr[v3]",
        "numcodecs>=0.12.0",
        "threadpoolctl",
        "psutil",
        "fabio",
        "pyinstaller",
    ]

    # Check which packages are missing
    missing_packages = []

    for package_spec in required_packages:
        # Extract package name (before version specifiers)
        package_name = package_spec.split('[')[0].split('>=')[0].split('==')[0].split('<')[0]

        try:
            __import__(package_name)
            print(f"  [OK] {package_name}")
        except ImportError:
            print(f"  [MISSING] {package_name}")
            missing_packages.append(package_spec)

    # Install missing packages
    if missing_packages:
        print(f"\nInstalling {len(missing_packages)} missing packages...")
        print("This may take several minutes...\n")

        for package in missing_packages:
            print(f"Installing {package}...")
            try:
                # Use --only-binary for packages that need C compilation (avoid MSVC requirement)
                # This forces pip to use pre-built wheels instead of compiling from source
                pip_args = [sys.executable, '-m', 'pip', 'install']

                # For packages with C extensions, use pre-built wheels only
                if any(pkg in package for pkg in ['numcodecs', 'mpi4py', 'psutil']):
                    pip_args.extend(['--only-binary', ':all:'])

                pip_args.append(package)

                result = subprocess.run(
                    pip_args,
                    capture_output=True,
                    text=True,
                    check=True
                )
                print(f"  [OK] {package} installed")
            except subprocess.CalledProcessError as e:
                print(f"  [FAIL] Failed to install {package}")
                print(f"    Error: {e.stderr}")
                return False

        print("\n[OK] All dependencies installed successfully!")
    else:
        print("\n[OK] All dependencies already installed!")

    return True


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        version = PyInstaller.__version__
        print(f"✓ PyInstaller {version} found")
        return True
    except ImportError:
        print("✗ PyInstaller not installed")
        print("\nInstall with: pip install pyinstaller")
        return False


def create_icon_if_missing(icon_path):
    """Create icon file if it doesn't exist."""
    if icon_path.exists():
        print(f"✓ Icon exists: {icon_path}")
        return True

    print(f"Icon not found, creating default icon...")

    try:
        # Run create_icon.py
        result = subprocess.run(
            [sys.executable, str(icon_path.parent / 'create_icon.py')],
            cwd=str(icon_path.parent),
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            if icon_path.exists():
                print(f"✓ Created icon: {icon_path}")
                return True
            else:
                print(f"✗ Icon creation failed: file not found after script")
                return False
        else:
            print(f"✗ Icon creation failed:")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"✗ Icon creation error: {e}")
        return False


def clean_build_directories(root_dir):
    """Remove previous build artifacts."""
    print("\nCleaning previous builds...")

    dirs_to_remove = ['build', 'dist']

    for dir_name in dirs_to_remove:
        dir_path = root_dir / dir_name
        if dir_path.exists():
            print(f"  Removing: {dir_path}")
            shutil.rmtree(dir_path)

    # Also remove PyInstaller cache
    pycache_dirs = list(root_dir.rglob('__pycache__'))
    for cache_dir in pycache_dirs:
        shutil.rmtree(cache_dir, ignore_errors=True)

    print("✓ Clean complete")


def build_executable(spec_file, root_dir):
    """
    Build executable using PyInstaller.

    Args:
        spec_file: Path to .spec file
        root_dir: PRISMA root directory

    Returns:
        True if successful
    """
    print("\nBuilding PRISMA.exe...")
    print(f"  Spec file: {spec_file}")
    print(f"  Working directory: {root_dir}")
    print("\nThis may take several minutes...\n")

    try:
        # Set environment variable to signal PyInstaller build
        # This allows GSAS-II import to be skipped during build analysis
        build_env = os.environ.copy()
        build_env['PYINSTALLER_BUILD'] = '1'

        # Run PyInstaller
        result = subprocess.run(
            [sys.executable, '-m', 'PyInstaller', str(spec_file), '--clean'],
            cwd=str(root_dir),
            env=build_env,
            capture_output=True,
            text=True
        )

        # Show output
        if result.stdout:
            print(result.stdout)

        if result.returncode == 0:
            print("\n✓ Build successful!")
            return True
        else:
            print("\n✗ Build failed!")
            if result.stderr:
                print("Error output:")
                print(result.stderr)
            return False

    except Exception as e:
        print(f"\n✗ Build error: {e}")
        return False


def verify_executable(exe_path):
    """
    Verify the built executable exists and get info.

    Args:
        exe_path: Path to PRISMA.exe

    Returns:
        True if valid
    """
    print("\nVerifying executable...")

    if not exe_path.exists():
        print(f"✗ Executable not found: {exe_path}")
        return False

    print(f"✓ Executable found: {exe_path}")

    # Get file size
    size_bytes = exe_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    print(f"  Size: {size_mb:.1f} MB")

    # Try to get version info (on Windows)
    if sys.platform == 'win32':
        try:
            from XRD import __version__
            print(f"  Version: {__version__}")
        except:
            print("  Version: Unknown")

    return True


def create_readme(dist_dir):
    """Create README in dist directory."""
    readme_path = dist_dir / 'README.txt'

    with open(readme_path, 'w') as f:
        f.write("PRISMA - Portable Executable\n")
        f.write("="*60 + "\n\n")
        f.write("This directory contains the standalone PRISMA executable.\n\n")
        f.write("Files:\n")
        f.write("  PRISMA.exe - Main application\n\n")
        f.write("To run:\n")
        f.write("  Double-click PRISMA.exe\n\n")
        f.write("Note: GSAS-II must be installed separately.\n")
        f.write("Configure GSAS-II path in PRISMA settings on first launch.\n\n")
        f.write("For installation with auto-setup, use PRISMA-Installer.exe\n")

    print(f"\n✓ Created README: {readme_path}")


def main():
    """Main build process."""
    parser = argparse.ArgumentParser(description="Build PRISMA.exe executable")
    parser.add_argument('--clean', action='store_true', help='Clean before build')
    args = parser.parse_args()

    print("="*60)
    print("PRISMA Executable Builder")
    print("="*60)

    # Determine paths
    installer_dir = Path(__file__).parent
    root_dir = installer_dir.parent
    spec_file = installer_dir / 'PRISMA.spec'
    icon_path = installer_dir / 'prisma_icon.ico'
    dist_dir = root_dir / 'dist'
    exe_path = dist_dir / 'PRISMA.exe'

    # CRITICAL: Check and install dependencies FIRST
    # This ensures PyInstaller can bundle all required packages
    if not check_and_install_dependencies():
        print("\n✗ Failed to install required dependencies")
        print("Please check your internet connection and pip configuration")
        return 1

    # Check PyInstaller (should be installed by dependencies check)
    if not check_pyinstaller():
        return 1

    # Create icon if needed
    if not create_icon_if_missing(icon_path):
        print("\nWarning: Proceeding without icon")

    # Clean if requested
    if args.clean:
        clean_build_directories(root_dir)

    # Check spec file exists
    if not spec_file.exists():
        print(f"\n✗ Spec file not found: {spec_file}")
        return 1

    print(f"✓ Spec file found: {spec_file}")

    # Build executable
    if not build_executable(spec_file, root_dir):
        return 1

    # Verify result
    if not verify_executable(exe_path):
        return 1

    # Create README
    create_readme(dist_dir)

    # Success summary
    print("\n" + "="*60)
    print("Build Complete!")
    print("="*60)
    print(f"\nExecutable: {exe_path}")
    print(f"Directory: {dist_dir}")
    print("\nNext steps:")
    print("  1. Test PRISMA.exe manually")
    print("  2. Use installer/build_installer.py to create installer")
    print("="*60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
