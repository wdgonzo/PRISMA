#!/usr/bin/env python3
"""
PRISMA Installer Builder
=========================
Builds PRISMA-Installer.exe using Inno Setup.

Usage:
    python build_installer.py

Requirements:
    - Inno Setup 6.2+ installed
    - PRISMA.exe already built (in dist/ directory)
    - Run build_exe.py first if PRISMA.exe doesn't exist

Output:
    installer/Output/PRISMA-Installer-v0.3.0-beta.exe

Author: William Gonzalez
Date: November 2025
Version: Beta 0.3
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path


def find_inno_setup_compiler():
    """
    Find Inno Setup compiler (iscc.exe).

    Returns:
        Path to iscc.exe or None if not found
    """
    # Common installation paths
    common_paths = [
        # Winget installation (user AppData)
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe")),
        # Standard installations
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 5\ISCC.exe"),
    ]

    for path in common_paths:
        if path.exists():
            print(f"✓ Found Inno Setup: {path}")
            return path

    # Try PATH
    try:
        result = subprocess.run(
            ['where', 'iscc'],
            capture_output=True,
            text=True,
            shell=True
        )

        if result.returncode == 0:
            path = Path(result.stdout.strip().split('\n')[0])
            if path.exists():
                print(f"✓ Found Inno Setup in PATH: {path}")
                return path
    except:
        pass

    return None


def check_prerequisites(root_dir):
    """
    Check if all prerequisites are met.

    Args:
        root_dir: PRISMA root directory

    Returns:
        True if all prerequisites met
    """
    print("\nChecking prerequisites...")

    all_ok = True

    # Check PRISMA.exe exists
    exe_path = root_dir / 'dist' / 'PRISMA.exe'
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"✓ PRISMA.exe found ({size_mb:.1f} MB)")
    else:
        print(f"✗ PRISMA.exe not found at: {exe_path}")
        print("  Run build_exe.py first to create PRISMA.exe")
        all_ok = False

    # Check LICENSE file (create placeholder if missing)
    license_path = root_dir / 'LICENSE'
    if not license_path.exists():
        print("⚠ LICENSE file not found, creating placeholder...")
        with open(license_path, 'w') as f:
            f.write("License: To Be Determined\n\n")
            f.write("PRISMA - Parallel Refinement and Integration System for Multi-Azimuthal Analysis\n\n")
            f.write("Copyright (c) 2025 William Gonzalez, Adrian Guzman, Luke Davenport\n\n")
            f.write("License terms to be determined before public release.\n")
        print(f"✓ Created placeholder LICENSE: {license_path}")
    else:
        print(f"✓ LICENSE file found")

    # Check icon exists
    icon_path = root_dir / 'installer' / 'prisma_icon.ico'
    if icon_path.exists():
        print(f"✓ Icon file found")
    else:
        print(f"⚠ Icon file not found: {icon_path}")
        print("  Installer will proceed without icon")

    return all_ok


def compile_installer(iscc_path, iss_file, installer_dir):
    """
    Compile Inno Setup script.

    Args:
        iscc_path: Path to iscc.exe
        iss_file: Path to .iss script
        installer_dir: Installer directory

    Returns:
        True if successful
    """
    print("\nCompiling installer...")
    print(f"  Script: {iss_file}")
    print("\nThis may take several minutes...\n")

    try:
        # Run Inno Setup compiler
        result = subprocess.run(
            [str(iscc_path), str(iss_file)],
            cwd=str(installer_dir),
            capture_output=True,
            text=True
        )

        # Show output
        if result.stdout:
            print(result.stdout)

        if result.returncode == 0:
            print("\n✓ Compilation successful!")
            return True
        else:
            print("\n✗ Compilation failed!")
            if result.stderr:
                print("Error output:")
                print(result.stderr)
            return False

    except Exception as e:
        print(f"\n✗ Compilation error: {e}")
        return False


def verify_installer(output_dir):
    """
    Verify installer was created and get info.

    Args:
        output_dir: Output directory

    Returns:
        Path to installer if found, None otherwise
    """
    print("\nVerifying installer...")

    # Find installer file (starts with PRISMA-Installer)
    installer_files = list(output_dir.glob('PRISMA-Installer*.exe'))

    if not installer_files:
        print(f"✗ Installer not found in: {output_dir}")
        return None

    installer_path = installer_files[0]
    print(f"✓ Installer found: {installer_path.name}")

    # Get file size
    size_bytes = installer_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    print(f"  Size: {size_mb:.1f} MB")

    return installer_path


def create_checksum(installer_path):
    """
    Create SHA256 checksum file for installer.

    Args:
        installer_path: Path to installer

    Returns:
        Path to checksum file
    """
    import hashlib

    print("\nGenerating checksum...")

    # Calculate SHA256
    sha256_hash = hashlib.sha256()

    with open(installer_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    checksum = sha256_hash.hexdigest()

    # Write checksum file
    checksum_file = installer_path.parent / f"{installer_path.stem}.sha256"

    with open(checksum_file, 'w') as f:
        f.write(f"{checksum}  {installer_path.name}\n")

    print(f"✓ Checksum created: {checksum_file.name}")
    print(f"  SHA256: {checksum}")

    return checksum_file


def main():
    """Main build process."""
    print("="*60)
    print("PRISMA Installer Builder")
    print("="*60)

    # Determine paths
    installer_dir = Path(__file__).parent
    root_dir = installer_dir.parent
    iss_file = installer_dir / 'prisma_installer.iss'
    output_dir = installer_dir / 'Output'

    # Find Inno Setup
    iscc_path = find_inno_setup_compiler()

    if not iscc_path:
        print("\n✗ Inno Setup not found!")
        print("\nPlease install Inno Setup:")
        print("  Download from: https://jrsoftware.org/isdl.php")
        print("  Install to default location")
        return 1

    # Check prerequisites
    if not check_prerequisites(root_dir):
        print("\n✗ Prerequisites not met!")
        return 1

    # Check ISS file exists
    if not iss_file.exists():
        print(f"\n✗ Installer script not found: {iss_file}")
        return 1

    print(f"✓ Installer script found: {iss_file}")

    # Compile installer
    if not compile_installer(iscc_path, iss_file, installer_dir):
        return 1

    # Verify output
    installer_path = verify_installer(output_dir)

    if not installer_path:
        return 1

    # Create checksum
    checksum_file = create_checksum(installer_path)

    # Success summary
    print("\n" + "="*60)
    print("Build Complete!")
    print("="*60)
    print(f"\nInstaller: {installer_path}")
    print(f"Checksum: {checksum_file}")
    print(f"\nNext steps:")
    print("  1. Test installer on a clean Windows VM")
    print("  2. Upload to GitHub Releases:")
    print(f"     - {installer_path.name}")
    print(f"     - {checksum_file.name}")
    print("  3. Update README.md with download link")
    print("="*60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
