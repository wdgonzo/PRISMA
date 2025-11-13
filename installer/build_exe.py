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
        # Run PyInstaller
        result = subprocess.run(
            [sys.executable, '-m', 'PyInstaller', str(spec_file), '--clean'],
            cwd=str(root_dir),
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

    # Check PyInstaller
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
