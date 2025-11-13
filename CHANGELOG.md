# Changelog

All notable changes to PRISMA will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0-beta] - 2025-11-13

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

## [0.2.0-beta] - 2025-10-XX

### Added
- Multi-frame image support (`.edf`, `.edf.GE5` formats)
- Dask-MPI HPC deployment support
- Advanced compression with Zarr v3 BloscCodec
- GSAS-II performance optimizations (caching, adaptive blkSize)
- Performance monitoring and benchmarking suite
- HPC environment optimization (thread management, BLAS detection)
- Advanced chunking strategy (100MB target optimization)

### Changed
- Improved processing speed (3-5x faster overall)
- Storage efficiency improved (75-90% compression)
- Memory efficiency enhanced (40-60% reduction)

---

## [0.1.0-beta] - 2025-09-XX

### Added
- Initial beta release
- Recipe-based XRD data processing
- GSAS-II integration for peak fitting
- 4D XRDDataset structure (peaks, frames, azimuths, measurements)
- Recipe Builder GUI for creating processing recipes
- Data Analyzer GUI for visualization
- Batch processor for multi-recipe processing
- Zarr-based data persistence
- Heatmap visualization generation
- Basic HPC support with Dask distributed

### Features
- Supports Pilatus detector `.tif` images
- Multi-peak fitting (110, 200, 211 Miller indices)
- Strain analysis relative to reference images
- CSV and PNG export capabilities
- Cross-platform support (Windows, Linux)

---

## Future Releases

### Planned for 1.0.0 (Production Release)
- Full documentation and user manual
- Comprehensive test suite
- License finalization (MIT or Apache 2.0)
- Linux installer support
- macOS support (if requested)
- Plugin system for custom analysis workflows
- Enhanced error reporting and logging
