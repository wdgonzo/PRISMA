#!/usr/bin/env python3
"""
PRISMA Unified Launcher
=======================
Main entry point for PRISMA application.

Launches the unified GUI with tabs for:
- Recipe Builder
- Batch Processor
- Data Analyzer

For headless operation (HPC), automatically falls back to CLI mode.

Usage:
    python run_prisma.py              # Launch GUI (or CLI if headless)
    python run_prisma.py --help       # Show help
    python run_prisma.py --verify     # Verify installation

Author(s): William Gonzalez, Adrian Guzman, Luke Davenport
Date: November 2025
Version: Beta 0.3
"""

import sys
import os
import argparse


def initialize_gsas_path():
    """
    Initialize GSAS-II path from config before any XRD imports.

    This is critical for PyInstaller-bundled executables where GSAS-II
    is installed separately and must be added to sys.path at runtime.

    Returns:
        True if GSAS path configured successfully, False otherwise
    """
    try:
        # Import config manager (no XRD dependencies)
        from pathlib import Path
        import json

        # Load config file
        config_path = Path.home() / '.prisma' / 'config.json'

        if not config_path.exists():
            # Config doesn't exist yet (first launch) - will be configured by GUI
            return False

        # Read GSAS path from config
        with open(config_path, 'r') as f:
            config = json.load(f)

        gsas_path = config.get('gsas_path')

        # Validate and add to sys.path
        if gsas_path and os.path.exists(gsas_path):
            # Add to beginning of sys.path for imports
            if gsas_path not in sys.path:
                sys.path.insert(0, gsas_path)

            # Set environment variable (GSAS-II internal use)
            os.environ['GSAS2DIR'] = gsas_path

            return True
        else:
            # GSAS path not configured or invalid
            return False

    except Exception as e:
        # Don't crash if config loading fails - will be handled by GUI
        print(f"Warning: Could not initialize GSAS-II path: {e}")
        return False


def is_headless():
    """
    Check if running in headless environment (no display).

    Returns:
        True if headless (HPC, SSH without X11, etc.)
    """
    # Windows always has display
    if sys.platform == 'win32':
        return False

    # Linux/Unix: check DISPLAY environment variable
    if 'DISPLAY' not in os.environ:
        return True

    # Check if can actually create a display
    try:
        from PyQt5.QtWidgets import QApplication
        # Try to create app (doesn't show anything)
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        return False
    except Exception:
        return True


def launch_gui():
    """Launch PRISMA GUI application."""
    from XRD.gui.main_launcher import main
    main()


def launch_cli():
    """Launch PRISMA CLI interface (for headless environments)."""
    print("="*60)
    print("PRISMA - Headless Mode")
    print("="*60)
    print("\nRunning in headless environment (no display detected).")
    print("\nAvailable commands:")
    print("  python run_batch_processor.py        - Process recipe batches")
    print("  python run_batch_processor.py --help - Show batch processor help")
    print("\nFor GUI access, use X11 forwarding or run on a system with display.")
    print("="*60)


def verify_installation():
    """Run installation verification."""
    try:
        from XRD.tools.verify_installation import main as verify_main
        verify_main()
    except ImportError:
        print("Error: Installation verification module not found.")
        print("Please ensure PRISMA is properly installed.")
        sys.exit(1)


def main():
    """Main entry point with command-line argument parsing."""
    # CRITICAL: Initialize GSAS-II path BEFORE any XRD imports
    # This loads the GSAS path from config and adds it to sys.path
    # Required for PyInstaller-bundled executables
    initialize_gsas_path()

    parser = argparse.ArgumentParser(
        description="PRISMA - Parallel Refinement and Integration System for Multi-Azimuthal Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s              Launch PRISMA GUI
  %(prog)s --verify     Verify installation
  %(prog)s --version    Show version

For headless operation (HPC), use run_batch_processor.py instead.
        """
    )

    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify PRISMA installation'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.3.0-beta'
    )

    args = parser.parse_args()

    # Handle verification
    if args.verify:
        verify_installation()
        return

    # Launch appropriate interface
    if is_headless():
        launch_cli()
    else:
        launch_gui()


if __name__ == "__main__":
    main()
