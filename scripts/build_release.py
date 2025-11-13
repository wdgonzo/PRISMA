#!/usr/bin/env python3
"""
PRISMA Release Builder
======================
Master build script that creates complete release package.

Orchestrates:
1. PyInstaller build → PRISMA.exe
2. Inno Setup build → PRISMA-Installer.exe
3. Checksum generation
4. Release package creation

Usage:
    python build_release.py [--version 0.3.0-beta]

Output:
    releases/v0.3.0-beta/
    ├── PRISMA-Installer-v0.3.0-beta.exe
    ├── PRISMA-Installer-v0.3.0-beta.exe.sha256
    └── RELEASE_NOTES.md

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
from datetime import datetime


def get_version_from_code():
    """
    Read version from XRD/__init__.py.

    Returns:
        Version string (e.g., "0.3.0-beta")
    """
    init_file = Path(__file__).parent.parent / 'XRD' / '__init__.py'

    try:
        with open(init_file, 'r') as f:
            for line in f:
                if line.startswith('__version__'):
                    # Extract version from __version__ = "0.3.0-beta"
                    version = line.split('"')[1]
                    return version
    except Exception as e:
        print(f"Warning: Could not read version from {init_file}: {e}")

    return None


def run_build_script(script_path, description, args=None):
    """
    Run a build script and capture output.

    Args:
        script_path: Path to Python script
        description: Description for output
        args: Additional command-line arguments (list)

    Returns:
        True if successful
    """
    print("\n" + "="*60)
    print(f"{description}")
    print("="*60)

    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)

    try:
        result = subprocess.run(
            cmd,
            cwd=script_path.parent,
            capture_output=False,  # Show output in real-time
            text=True
        )

        if result.returncode == 0:
            print(f"\n✓ {description} - SUCCESS")
            return True
        else:
            print(f"\n✗ {description} - FAILED")
            return False

    except Exception as e:
        print(f"\n✗ {description} - ERROR: {e}")
        return False


def create_release_notes(version, release_dir):
    """
    Create release notes file.

    Args:
        version: Version string
        release_dir: Release directory

    Returns:
        Path to release notes file
    """
    notes_file = release_dir / 'RELEASE_NOTES.md'

    # Read changelog to get version-specific notes
    changelog_file = release_dir.parent.parent / 'CHANGELOG.md'
    version_notes = ""

    if changelog_file.exists():
        try:
            with open(changelog_file, 'r') as f:
                in_version_section = False
                for line in f:
                    if line.startswith(f'## [{version}]'):
                        in_version_section = True
                        continue
                    elif line.startswith('## [') and in_version_section:
                        break
                    elif in_version_section:
                        version_notes += line
        except Exception as e:
            print(f"Warning: Could not read changelog: {e}")

    # Create release notes
    with open(notes_file, 'w') as f:
        f.write(f"# PRISMA {version} - Release Notes\n\n")
        f.write(f"**Release Date**: {datetime.now().strftime('%Y-%m-%d')}\n\n")

        f.write("## Installation\n\n")
        f.write(f"Download `PRISMA-Installer-v{version}.exe` and run it.\n\n")
        f.write("**System Requirements**:\n")
        f.write("- Windows 10 version 1809 or later (64-bit)\n")
        f.write("- 4GB RAM minimum, 8GB recommended\n")
        f.write("- 2GB disk space for PRISMA + ~500MB for GSAS-II\n")
        f.write("- Git (for automatic GSAS-II download)\n\n")

        f.write("**Installation Steps**:\n")
        f.write("1. Download the installer\n")
        f.write("2. Run `PRISMA-Installer.exe` (requires administrator)\n")
        f.write("3. Follow the installation wizard\n")
        f.write("4. Launch PRISMA from desktop shortcut or Start Menu\n\n")

        if version_notes:
            f.write("## What's New\n\n")
            f.write(version_notes)
        else:
            f.write("## What's New\n\n")
            f.write("See CHANGELOG.md for full details.\n\n")

        f.write("## Verification\n\n")
        f.write("SHA256 checksums are provided for verification:\n")
        f.write(f"- `PRISMA-Installer-v{version}.exe.sha256`\n\n")
        f.write("Verify with:\n")
        f.write("```powershell\n")
        f.write(f"certutil -hashfile PRISMA-Installer-v{version}.exe SHA256\n")
        f.write("```\n\n")

        f.write("## Known Issues\n\n")
        f.write("- Recipe Builder and Data Analyzer tabs show placeholder text\n")
        f.write("  - Use standalone scripts for now: `run_recipe_builder.py`, `run_data_analyzer.py`\n")
        f.write("  - Full integration coming in v0.4.0\n\n")

        f.write("## Support\n\n")
        f.write("- Report issues: https://github.com/wdgonzo/PRISMA/issues\n")
        f.write("- Documentation: https://github.com/wdgonzo/PRISMA/blob/main/README.md\n\n")

        f.write("## Credits\n\n")
        f.write("PRISMA development team:\n")
        f.write("- William Gonzalez\n")
        f.write("- Adrian Guzman\n")
        f.write("- Luke Davenport\n\n")

        f.write("PRISMA uses GSAS-II (Advanced Photon Source, Argonne National Laboratory)\n")

    print(f"✓ Created release notes: {notes_file}")
    return notes_file


def copy_installer_to_release(installer_dir, release_dir, version):
    """
    Copy installer and checksum to release directory.

    Args:
        installer_dir: Installer directory
        release_dir: Release directory
        version: Version string

    Returns:
        True if successful
    """
    print("\nCopying files to release directory...")

    output_dir = installer_dir / 'Output'

    # Find installer
    installer_files = list(output_dir.glob(f'PRISMA-Installer-v{version}.exe'))

    if not installer_files:
        print(f"✗ Installer not found: PRISMA-Installer-v{version}.exe")
        return False

    installer_src = installer_files[0]
    installer_dst = release_dir / installer_src.name

    # Copy installer
    shutil.copy2(installer_src, installer_dst)
    print(f"✓ Copied: {installer_dst.name}")

    # Copy checksum if exists
    checksum_src = installer_src.parent / f"{installer_src.stem}.sha256"
    if checksum_src.exists():
        checksum_dst = release_dir / checksum_src.name
        shutil.copy2(checksum_src, checksum_dst)
        print(f"✓ Copied: {checksum_dst.name}")

    return True


def main():
    """Main build orchestration."""
    parser = argparse.ArgumentParser(description="Build complete PRISMA release")
    parser.add_argument('--version', help='Version to build (default: read from code)')
    parser.add_argument('--skip-exe', action='store_true', help='Skip PRISMA.exe build')
    parser.add_argument('--skip-installer', action='store_true', help='Skip installer build')
    args = parser.parse_args()

    print("="*60)
    print("PRISMA Release Builder")
    print("="*60)

    # Determine paths
    root_dir = Path(__file__).parent.parent
    installer_dir = root_dir / 'installer'
    scripts_dir = root_dir / 'scripts'
    releases_dir = root_dir / 'releases'

    # Determine version
    if args.version:
        version = args.version
    else:
        version = get_version_from_code()

    if not version:
        print("✗ Could not determine version!")
        print("  Specify with --version or check XRD/__init__.py")
        return 1

    print(f"\nBuilding version: {version}")

    # Create release directory
    release_dir = releases_dir / f"v{version}"
    release_dir.mkdir(parents=True, exist_ok=True)
    print(f"Release directory: {release_dir}")

    # Step 1: Build PRISMA.exe
    if not args.skip_exe:
        success = run_build_script(
            installer_dir / 'build_exe.py',
            "Step 1: Building PRISMA.exe",
            ['--clean']
        )

        if not success:
            print("\n✗ PRISMA.exe build failed!")
            return 1
    else:
        print("\n⏭ Skipping PRISMA.exe build (--skip-exe)")

    # Step 2: Build Installer
    if not args.skip_installer:
        success = run_build_script(
            installer_dir / 'build_installer.py',
            "Step 2: Building PRISMA-Installer.exe"
        )

        if not success:
            print("\n✗ Installer build failed!")
            return 1
    else:
        print("\n⏭ Skipping installer build (--skip-installer)")

    # Step 3: Copy files to release directory
    print("\n" + "="*60)
    print("Step 3: Creating Release Package")
    print("="*60)

    if not copy_installer_to_release(installer_dir, release_dir, version):
        print("\n✗ Failed to copy installer to release directory!")
        return 1

    # Step 4: Create release notes
    create_release_notes(version, release_dir)

    # Step 5: List release contents
    print("\n" + "="*60)
    print("Release Package Complete!")
    print("="*60)
    print(f"\nRelease: v{version}")
    print(f"Location: {release_dir.absolute()}")
    print("\nContents:")

    for file in sorted(release_dir.iterdir()):
        if file.is_file():
            size_mb = file.stat().st_size / (1024 * 1024)
            print(f"  {file.name:50} ({size_mb:>8.1f} MB)")

    # Step 6: Next steps
    print("\n" + "="*60)
    print("Next Steps")
    print("="*60)
    print("\n1. Test installer on clean Windows VM")
    print("   - Install and verify all functionality")
    print("   - Test GSAS-II auto-setup")
    print("   - Test desktop shortcut\n")
    print("2. Create GitHub release:")
    print(f"   - Tag: v{version}")
    print("   - Upload files from: {release_dir}")
    print("   - Copy RELEASE_NOTES.md to release description\n")
    print("3. Update README.md:")
    print("   - Add download link to release")
    print("   - Update screenshots if needed\n")
    print("4. Announce release:")
    print("   - Social media / mailing list")
    print("   - Update project documentation")
    print("="*60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
