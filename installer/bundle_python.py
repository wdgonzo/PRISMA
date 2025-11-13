#!/usr/bin/env python3
"""
Python Bundle Creator
=====================
Downloads and configures a portable Python distribution for PRISMA installer.

Creates a self-contained Python environment with all dependencies installed.
Used by the Windows installer to bundle Python with PRISMA.

Usage:
    python bundle_python.py [--python-version 3.11.9] [--output-dir python_bundle]

Requirements:
    - Internet connection (to download Python embeddable package)
    - ~200MB disk space for Python bundle

Output:
    - python_bundle/ directory with complete Python environment
    - All PRISMA dependencies pre-installed

Author(s): William Gonzalez
Date: November 2025
Version: Beta 0.3
"""

import os
import sys
import urllib.request
import zipfile
import subprocess
import shutil
import argparse
from pathlib import Path


# Python embeddable package URLs (Windows only)
PYTHON_VERSIONS = {
    '3.11.9': 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip',
    '3.12.0': 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-embed-amd64.zip',
}

GET_PIP_URL = 'https://bootstrap.pypa.io/get-pip.py'


def download_file(url, dest_path, description="file"):
    """
    Download file with progress indicator.

    Args:
        url: URL to download
        dest_path: Destination file path
        description: Description for progress message
    """
    print(f"Downloading {description}...")
    print(f"  URL: {url}")
    print(f"  Destination: {dest_path}")

    def progress_hook(block_num, block_size, total_size):
        """Show download progress."""
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100, downloaded * 100 // total_size)
            bar_length = 40
            filled = int(bar_length * percent / 100)
            bar = '=' * filled + '-' * (bar_length - filled)
            sys.stdout.write(f'\r  [{bar}] {percent}%')
            sys.stdout.flush()

    try:
        urllib.request.urlretrieve(url, dest_path, progress_hook)
        print("\n  Download complete!")
        return True
    except Exception as e:
        print(f"\n  Error downloading: {e}")
        return False


def extract_zip(zip_path, extract_dir):
    """
    Extract ZIP file.

    Args:
        zip_path: Path to ZIP file
        extract_dir: Directory to extract to
    """
    print(f"Extracting {zip_path}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        print("  Extraction complete!")
        return True
    except Exception as e:
        print(f"  Error extracting: {e}")
        return False


def setup_python_bundle(python_version='3.11.9', output_dir='python_bundle'):
    """
    Create portable Python bundle with PRISMA dependencies.

    Args:
        python_version: Python version to bundle (e.g., '3.11.9')
        output_dir: Output directory for bundle

    Returns:
        True if successful
    """
    print("="*60)
    print("PRISMA Python Bundle Creator")
    print("="*60)

    if python_version not in PYTHON_VERSIONS:
        print(f"Error: Python version {python_version} not supported.")
        print(f"Available versions: {', '.join(PYTHON_VERSIONS.keys())}")
        return False

    # Create output directory
    output_path = Path(output_dir)
    if output_path.exists():
        print(f"\nWarning: Output directory exists: {output_path}")
        response = input("Delete and recreate? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return False
        shutil.rmtree(output_path)

    output_path.mkdir(parents=True, exist_ok=True)

    # Download Python embeddable package
    print(f"\n[1/5] Downloading Python {python_version} embeddable package...")
    python_url = PYTHON_VERSIONS[python_version]
    python_zip = output_path / 'python_embed.zip'

    if not download_file(python_url, python_zip, f"Python {python_version}"):
        return False

    # Extract Python
    print(f"\n[2/5] Extracting Python...")
    if not extract_zip(python_zip, output_path):
        return False

    # Clean up ZIP
    python_zip.unlink()

    # Download get-pip.py
    print(f"\n[3/5] Downloading pip installer...")
    get_pip_path = output_path / 'get-pip.py'

    if not download_file(GET_PIP_URL, get_pip_path, "get-pip.py"):
        return False

    # Install pip
    print(f"\n[4/5] Installing pip...")
    python_exe = output_path / 'python.exe'

    # First, need to modify python*._pth file to enable site-packages
    pth_files = list(output_path.glob('python*._pth'))
    if pth_files:
        pth_file = pth_files[0]
        print(f"  Modifying {pth_file.name} to enable site-packages...")

        with open(pth_file, 'r') as f:
            lines = f.readlines()

        with open(pth_file, 'w') as f:
            for line in lines:
                # Uncomment import site line
                if line.strip().startswith('#import site'):
                    f.write('import site\n')
                else:
                    f.write(line)

    # Run get-pip.py
    try:
        result = subprocess.run(
            [str(python_exe), str(get_pip_path)],
            cwd=str(output_path),
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("  Pip installed successfully!")
        else:
            print(f"  Error installing pip:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"  Error running pip installer: {e}")
        return False

    # Clean up get-pip.py
    get_pip_path.unlink()

    # Install PRISMA dependencies
    print(f"\n[5/5] Installing PRISMA dependencies...")

    # Read requirements from file
    requirements_file = Path(__file__).parent.parent / 'requirements.txt'

    if not requirements_file.exists():
        print(f"  Error: requirements.txt not found at {requirements_file}")
        return False

    print(f"  Using requirements from: {requirements_file}")

    # Install using pip
    pip_exe = output_path / 'Scripts' / 'pip.exe'
    if not pip_exe.exists():
        # Try alternate location
        pip_exe = output_path / 'Scripts' / 'pip3.exe'

    if not pip_exe.exists():
        print("  Error: pip executable not found after installation")
        return False

    try:
        print("  Installing dependencies (this may take several minutes)...")
        result = subprocess.run(
            [str(pip_exe), 'install', '-r', str(requirements_file)],
            cwd=str(output_path),
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("  All dependencies installed successfully!")
        else:
            print(f"  Error installing dependencies:")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"  Error running pip: {e}")
        return False

    # Verify installation
    print("\nVerifying installation...")
    critical_packages = ['numpy', 'PyQt5', 'zarr', 'dask']

    all_good = True
    for package in critical_packages:
        try:
            result = subprocess.run(
                [str(python_exe), '-c', f'import {package}'],
                cwd=str(output_path),
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"  ✓ {package}")
            else:
                print(f"  ✗ {package} - FAILED")
                all_good = False

        except Exception as e:
            print(f"  ✗ {package} - Error: {e}")
            all_good = False

    if not all_good:
        print("\nWarning: Some packages failed to import.")
        print("The bundle may not work correctly.")
        return False

    # Create activation script
    print("\nCreating activation script...")
    activate_script = output_path / 'activate_prisma.bat'

    with open(activate_script, 'w') as f:
        f.write('@echo off\n')
        f.write(f'REM PRISMA Python Bundle Activation Script\n')
        f.write(f'REM Auto-generated by bundle_python.py\n\n')
        f.write(f'SET "PYTHONHOME=%~dp0"\n')
        f.write(f'SET "PYTHONPATH=%~dp0;%~dp0\\Lib;%~dp0\\DLLs"\n')
        f.write(f'SET "PATH=%~dp0;%~dp0\\Scripts;%PATH%"\n\n')
        f.write(f'echo PRISMA Python environment activated\n')
        f.write(f'echo Python: %~dp0python.exe\n')

    print(f"  Created: {activate_script}")

    # Calculate bundle size
    total_size = sum(f.stat().st_size for f in output_path.rglob('*') if f.is_file())
    size_mb = total_size / (1024 * 1024)

    print("\n" + "="*60)
    print("Python Bundle Created Successfully!")
    print("="*60)
    print(f"Location: {output_path.absolute()}")
    print(f"Size: {size_mb:.1f} MB")
    print(f"Python: {python_version}")
    print("\nThe bundle is ready to be included in the PRISMA installer.")
    print("="*60)

    return True


def main():
    """Main entry point with command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Create portable Python bundle for PRISMA installer"
    )

    parser.add_argument(
        '--python-version',
        default='3.11.9',
        choices=list(PYTHON_VERSIONS.keys()),
        help='Python version to bundle (default: 3.11.9)'
    )

    parser.add_argument(
        '--output-dir',
        default='python_bundle',
        help='Output directory for bundle (default: python_bundle)'
    )

    args = parser.parse_args()

    success = setup_python_bundle(
        python_version=args.python_version,
        output_dir=args.output_dir
    )

    if success:
        print("\n✓ Bundle creation complete!")
        return 0
    else:
        print("\n✗ Bundle creation failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
