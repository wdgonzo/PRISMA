#!/usr/bin/env python3
"""
GSAS-II Auto-Setup Script
==========================
Automated GSAS-II installation and configuration for PRISMA.

Features:
- Prompts user to download GSAS-II (or use existing installation)
- Clones GSAS-II repository from GitHub
- Configures environment variables
- Validates GSAS-II installation
- Creates activation script with proper paths

Usage:
    python setup_gsas.py [--install-dir C:\\path\\to\\install]
    python setup_gsas.py --existing C:\\path\\to\\existing\\GSAS-II

Author(s): William Gonzalez
Date: November 2025
Version: Beta 0.3
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, cwd=None, description="command"):
    """
    Run shell command with output.

    Args:
        cmd: Command to run (list or string)
        cwd: Working directory
        description: Description for user

    Returns:
        True if successful
    """
    print(f"\nRunning: {description}")
    print(f"  Command: {' '.join(cmd) if isinstance(cmd, list) else cmd}")

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            shell=isinstance(cmd, str)
        )

        if result.returncode == 0:
            print("  ✓ Success")
            if result.stdout:
                print(f"  Output: {result.stdout.strip()}")
            return True
        else:
            print("  ✗ Failed")
            if result.stderr:
                print(f"  Error: {result.stderr.strip()}")
            return False

    except Exception as e:
        print(f"  ✗ Exception: {e}")
        return False


def check_git_available():
    """
    Check if git is available in PATH.

    Returns:
        True if git is available
    """
    try:
        result = subprocess.run(
            ['git', '--version'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✓ Git available: {result.stdout.strip()}")
            return True
        else:
            return False
    except FileNotFoundError:
        print("✗ Git not found in PATH")
        print("\nPlease install Git:")
        print("  Download from: https://git-scm.com/download/win")
        return False


def clone_gsas(install_dir):
    """
    Clone GSAS-II repository from GitHub.

    Args:
        install_dir: Directory to clone into (will create GSAS-II subdirectory)

    Returns:
        Path to cloned GSAS-II directory or None if failed
    """
    gsas_url = 'https://github.com/AdvancedPhotonSource/GSAS-II.git'
    gsas_dir = Path(install_dir) / 'GSAS-II'

    print("\n" + "="*60)
    print("Cloning GSAS-II Repository")
    print("="*60)
    print(f"Source: {gsas_url}")
    print(f"Destination: {gsas_dir}")
    print("\nThis will download approximately 500MB of data.")
    print("Estimated time: 2-5 minutes depending on connection.")

    # Create install directory
    Path(install_dir).mkdir(parents=True, exist_ok=True)

    # Clone repository
    if gsas_dir.exists():
        print(f"\nWarning: Directory already exists: {gsas_dir}")
        response = input("Delete and re-clone? (y/n): ")
        if response.lower() == 'y':
            import shutil
            shutil.rmtree(gsas_dir)
        else:
            print("Using existing directory.")
            return gsas_dir

    success = run_command(
        ['git', 'clone', gsas_url, str(gsas_dir)],
        description="git clone GSAS-II"
    )

    if success and gsas_dir.exists():
        print(f"\n✓ GSAS-II cloned successfully to: {gsas_dir}")
        return gsas_dir
    else:
        print("\n✗ Failed to clone GSAS-II")
        return None


def validate_gsas_installation(gsas_dir):
    """
    Validate GSAS-II installation.

    Args:
        gsas_dir: Path to GSAS-II directory

    Returns:
        True if valid
    """
    print("\n" + "="*60)
    print("Validating GSAS-II Installation")
    print("="*60)

    gsas_path = Path(gsas_dir)

    # Check directory exists
    if not gsas_path.exists():
        print(f"✗ Directory not found: {gsas_path}")
        return False

    print(f"✓ Directory exists: {gsas_path}")

    # Check for GSASII subdirectory
    gsasii_subdir = gsas_path / 'GSASII'
    if not gsasii_subdir.exists():
        print(f"✗ GSASII subdirectory not found: {gsasii_subdir}")
        return False

    print(f"✓ GSASII subdirectory found")

    # Check for GSASIIscriptable.py
    scriptable_file = gsasii_subdir / 'GSASIIscriptable.py'
    if not scriptable_file.exists():
        print(f"✗ GSASIIscriptable.py not found: {scriptable_file}")
        return False

    print(f"✓ GSASIIscriptable.py found")

    # Try importing GSAS-II (add to path temporarily)
    sys.path.insert(0, str(gsas_path))

    try:
        from GSASII import GSASIIscriptable as G2sc
        print(f"✓ GSAS-II import successful")

        # Try getting version
        try:
            version_info = G2sc.version
            print(f"  GSAS-II version: {version_info}")
        except:
            print(f"  (Version info not available)")

        return True

    except ImportError as e:
        print(f"✗ Failed to import GSAS-II: {e}")
        return False

    finally:
        sys.path.pop(0)


def create_activation_script(install_dir, gsas_dir, output_file='activate_prisma.bat'):
    """
    Create batch script to activate PRISMA environment with GSAS-II.

    Args:
        install_dir: PRISMA installation directory
        gsas_dir: GSAS-II directory path
        output_file: Output filename for activation script

    Returns:
        Path to created script
    """
    print("\n" + "="*60)
    print("Creating Environment Activation Script")
    print("="*60)

    script_path = Path(install_dir) / output_file

    # Convert paths to Windows format
    gsas_dir_abs = Path(gsas_dir).absolute()
    install_dir_abs = Path(install_dir).absolute()

    with open(script_path, 'w') as f:
        f.write('@echo off\n')
        f.write('REM PRISMA Environment Activation Script\n')
        f.write('REM Auto-generated by setup_gsas.py\n\n')

        # Set GSAS-II paths
        f.write(f'SET "GSAS2DIR={gsas_dir_abs}"\n')
        f.write(f'SET "PYTHONPATH={gsas_dir_abs};%PYTHONPATH%"\n\n')

        # Add Python to PATH (if bundled)
        python_bundle = install_dir_abs / 'python_bundle'
        if python_bundle.exists():
            f.write(f'SET "PATH={python_bundle};{python_bundle}\\Scripts;%PATH%"\n')
            f.write(f'SET "PYTHONHOME={python_bundle}"\n\n')

        # Add PRISMA to PATH
        f.write(f'SET "PATH={install_dir_abs};%PATH%"\n\n')

        f.write('echo PRISMA environment activated\n')
        f.write('echo   GSAS-II: %GSAS2DIR%\n')
        if python_bundle.exists():
            f.write('echo   Python: %PYTHONHOME%\\python.exe\n')
        f.write('echo   PRISMA: %~dp0\n')

    print(f"✓ Created activation script: {script_path}")
    print("\nTo use PRISMA, run this script before launching:")
    print(f"  {script_path}")

    return script_path


def setup_gsas_interactive(install_dir=None):
    """
    Interactive GSAS-II setup.

    Args:
        install_dir: Installation directory (prompts if None)

    Returns:
        True if successful
    """
    print("="*60)
    print("PRISMA GSAS-II Setup Wizard")
    print("="*60)

    # Determine install directory
    if install_dir is None:
        print("\nWhere would you like to install GSAS-II?")
        print("  (This directory will contain a 'GSAS-II' subdirectory)")

        default_dir = str(Path.home() / "PRISMA")
        install_dir = input(f"\nInstallation directory [{default_dir}]: ").strip()

        if not install_dir:
            install_dir = default_dir

    install_dir = os.path.abspath(install_dir)

    print(f"\nInstallation directory: {install_dir}")

    # Ask user: download or use existing?
    print("\nGSAS-II Setup Options:")
    print("  1. Download and install GSAS-II (requires Git and ~500MB)")
    print("  2. Use existing GSAS-II installation")

    choice = input("\nSelect option (1 or 2): ").strip()

    gsas_dir = None

    if choice == '1':
        # Check Git availability
        if not check_git_available():
            return False

        # Clone GSAS-II
        gsas_dir = clone_gsas(install_dir)

        if not gsas_dir:
            return False

    elif choice == '2':
        # Prompt for existing GSAS-II directory
        gsas_dir = input("\nEnter path to existing GSAS-II directory: ").strip()

        if not gsas_dir:
            print("Error: No path provided")
            return False

        gsas_dir = os.path.abspath(gsas_dir)

    else:
        print("Error: Invalid choice")
        return False

    # Validate installation
    if not validate_gsas_installation(gsas_dir):
        print("\n✗ GSAS-II validation failed!")
        return False

    # Create activation script
    create_activation_script(install_dir, gsas_dir)

    print("\n" + "="*60)
    print("✓ GSAS-II Setup Complete!")
    print("="*60)
    print(f"\nGSAS-II location: {gsas_dir}")
    print(f"Installation directory: {install_dir}")
    print("\nNext steps:")
    print("  1. Run activate_prisma.bat to set up environment")
    print("  2. Launch PRISMA with: python run_prisma.py")
    print("="*60)

    return True


def main():
    """Main entry point with command-line arguments."""
    parser = argparse.ArgumentParser(
        description="GSAS-II auto-setup for PRISMA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Interactive setup
  %(prog)s --install-dir C:\\PRISMA           # Install to specific directory
  %(prog)s --existing C:\\path\\to\\GSAS-II   # Use existing installation
        """
    )

    parser.add_argument(
        '--install-dir',
        help='PRISMA installation directory'
    )

    parser.add_argument(
        '--existing',
        help='Path to existing GSAS-II installation (skip download)'
    )

    args = parser.parse_args()

    # Handle existing installation
    if args.existing:
        gsas_dir = os.path.abspath(args.existing)

        if not validate_gsas_installation(gsas_dir):
            print("\n✗ Invalid GSAS-II installation")
            return 1

        install_dir = args.install_dir or str(Path.home() / "PRISMA")
        create_activation_script(install_dir, gsas_dir)

        print("\n✓ GSAS-II configuration complete!")
        return 0

    # Interactive setup
    success = setup_gsas_interactive(install_dir=args.install_dir)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
