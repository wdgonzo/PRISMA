# PRISMA 0.3.0-beta - Release Notes

**Release Date**: 2025-11-13

## Installation

Download `PRISMA-Installer-v0.3.0-beta.exe` and run it.

**System Requirements**:
- Windows 10 version 1809 or later (64-bit)
- 4GB RAM minimum, 8GB recommended
- 2GB disk space for PRISMA + ~500MB for GSAS-II
- Git (for automatic GSAS-II download)

**Installation Steps**:
1. Download the installer
2. Run `PRISMA-Installer.exe` (requires administrator)
3. Follow the installation wizard
4. Launch PRISMA from desktop shortcut or Start Menu

## What's New


### Added
- **Unified Launcher GUI**: Single application window with tabs for Recipe Builder, Batch Processor, and Data Analyzer
- **Batch Processor GUI**: Visual interface for batch processing with real-time progress indicators
- **Auto-Update System**: Automatic update checking via GitHub releases with opt-out option
- **Configuration Management**: Centralized user settings and workspace management
- **Workspace Selection**: File menu for choosing and managing workspace directories
- **Windows Installer**: One-click `.exe` installer with bundled Python and auto-GSAS-II setup
- **Update Checker Module**: Background checking for new releases with user notifications
- **Installation Verification**: `prisma --verify` command to validate installation

### Changed
- **Version bumped to Beta 0.3**: Preparing for public release
- **Improved user experience**: Professional GUI layout with unified entry point
- **Settings persistence**: User preferences saved across sessions

### Maintained
- **Full HPC compatibility**: Headless mode still works on Crux and other HPC systems
- **Backward compatibility**: Old `run_*.py` scripts still functional for CLI/HPC workflows

---

## Verification

SHA256 checksums are provided for verification:
- `PRISMA-Installer-v0.3.0-beta.exe.sha256`

Verify with:
```powershell
certutil -hashfile PRISMA-Installer-v0.3.0-beta.exe SHA256
```

## Known Issues

- Recipe Builder and Data Analyzer tabs show placeholder text
  - Use standalone scripts for now: `run_recipe_builder.py`, `run_data_analyzer.py`
  - Full integration coming in v0.4.0

## Support

- Report issues: https://github.com/wdgonzo/PRISMA/issues
- Documentation: https://github.com/wdgonzo/PRISMA/blob/main/README.md

## Credits

PRISMA development team:
- William Gonzalez
- Adrian Guzman
- Luke Davenport

PRISMA uses GSAS-II (Advanced Photon Source, Argonne National Laboratory)
