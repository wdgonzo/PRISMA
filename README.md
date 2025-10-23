# PRISMA
## Parallel Refinement and Integration System for Multi-Azimuthal Analysis

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-Beta%200.1-orange.svg)](https://github.com/wdgonzo/PRISMA)

**PRISMA** is a comprehensive Python-based X-ray diffraction (XRD) data processing system for materials science analysis. Built on GSAS-II, it provides advanced peak fitting, strain analysis, and visualization capabilities optimized for both local workstations and HPC supercomputers.

## Features

### Core Capabilities
- **GSAS-II Integration**: Full integration with GSAS-II scripting for peak fitting and refinement
- **Multi-Format Support**: Process single-frame (.tif) and multi-frame (.edf, .edf.GE5) diffraction images
- **4D Data Structure**: Unified data array (peaks × frames × azimuths × measurements) for efficient processing
- **Parallel Processing**: Dask-based parallelization with automatic HPC/local mode detection
- **Zarr Storage**: Compressed, chunked data storage with 75-90% size reduction

### HPC Support
- **Dask-MPI**: Automatic multi-node scaling on supercomputers
- **Near-linear Scaling**: Up to 75% efficiency on 64 nodes
- **Headless Operation**: No GUI dependencies for batch processing
- **PBS Integration**: Job submission templates for HPC clusters

### Analysis & Visualization
- **Strain Mapping**: Calculate and visualize strain relative to reference states
- **Multi-Peak Analysis**: Simultaneous analysis of multiple Miller indices (110, 200, 211)
- **Interactive GUIs**: Recipe builder, data analyzer, and visualization interfaces
- **Publication-Ready Plots**: Heatmaps with configurable colormaps and locked limits

## Installation

### Requirements
- Python 3.8 or higher
- GSAS-II (separate installation required)
- Recommended: 16GB+ RAM for large datasets

### Quick Start

1. **Clone the repository**:
```bash
git clone https://github.com/wdgonzo/PRISMA.git
cd PRISMA
```

2. **Install Python dependencies**:
```bash
pip install -r requirements.txt
# Or use the initialization script:
python XRD/initialize.py
```

3. **Configure GSAS-II** (one-time setup):
```bash
python XRD/initialize_gsas_headless.py /path/to/GSAS-II
```

## Usage

### 1. Create a Processing Recipe

Launch the Recipe Builder GUI:
```bash
python run_recipe_builder.py
```

Or create a recipe JSON manually:
```json
{
  "sample": "Sample_A",
  "setting": "Pilatus",
  "stage": "BEF",
  "home_dir": "/path/to/data",
  "images_path": "/path/to/images",
  "control_file": "calibration.imctrl",
  "mask_file": "mask.immask",
  "active_peaks": [...],
  "az_start": -90,
  "az_end": 90,
  "spacing": 5,
  "frame_start": 0,
  "frame_end": 100,
  "step": 1
}
```

### 2. Process Data

**Local processing**:
```bash
python run_batch_processor.py my_recipe.json
```

**HPC processing** (automatic Dask-MPI):
```bash
mpiexec -n 32 python XRD/processing/batch_processor.py
```

### 3. Analyze and Visualize

Launch the Data Analyzer:
```bash
python run_data_analyzer.py
```

Or use command-line visualization:
```bash
python XRD/visualization/data_visualization.py '{"zarr_path": "path/to/data.zarr", "Map_Type": "strain", "Mode": "Robust", "Color": "icefire"}'
```

## Project Structure

```
PRISMA/
├── XRD/                          # Main package
│   ├── core/                     # Core processing modules
│   │   ├── gsas_processing.py    # GSAS-II integration & data structures
│   │   └── image_loader.py       # Multi-format image loading
│   ├── processing/               # Data processing workflows
│   │   ├── data_generator.py     # Main processing pipeline
│   │   ├── batch_processor.py    # Batch processing
│   │   └── recipes.py            # Recipe management
│   ├── visualization/            # Visualization modules
│   │   ├── data_visualization.py # Main visualization logic
│   │   └── plotting.py           # Plotting functions
│   ├── gui/                      # GUI applications
│   │   ├── recipe_builder.py     # Recipe creation GUI
│   │   └── data_analyzer.py      # Data analysis GUI
│   ├── utils/                    # Utility modules
│   │   ├── path_manager.py       # Path management
│   │   ├── filters.py            # Signal processing
│   │   └── calibration.py        # GSAS-II calibration
│   ├── hpc/                      # HPC support
│   │   └── cluster.py            # Dask-MPI integration
│   └── tools/                    # Diagnostic tools
│       ├── check_zarr.py         # Data inspection
│       └── performance_monitor.py # Performance analysis
├── docs/                         # Documentation
│   ├── CRUX_DEPLOYMENT.md        # HPC deployment guide
│   ├── MULTIFRAME_SUPPORT.md     # Multi-frame image guide
│   └── FILESTRUCTURE.md          # File organization guide
├── scripts/                      # HPC deployment scripts
│   └── crux_setup.sh             # Crux supercomputer setup
├── run_recipe_builder.py         # Recipe Builder launcher
├── run_data_analyzer.py          # Data Analyzer launcher
└── run_batch_processor.py        # Batch processor launcher
```

## Data Organization

PRISMA uses a structured directory system:

```
Home/
├── [Your Data]/                  # Raw images
│   ├── Images/                   # Diffraction images (.tif, .edf, .edf.GE5)
│   └── Refs/                     # Reference images (optional)
├── Processed/                    # Processed datasets
│   └── {Date}/
│       └── {Sample}/
│           └── Zarr/             # Compressed Zarr datasets
├── Analysis/                     # Analysis outputs
│   └── {Date}/
│       └── {Sample}/
│           ├── *.tiff            # Heatmap visualizations
│           └── *.csv             # Data exports
└── recipes/                      # Processing recipes
    └── *.json
```

## Performance

Typical processing speeds (Crux supercomputer):
- **Single node**: ~50 images/hour
- **4 nodes**: ~150 images/hour (3x speedup)
- **32 nodes**: ~1200 images/hour (24x speedup)

Storage efficiency:
- **Compression**: 75-90% file size reduction
- **Example**: 50GB raw data → 5GB compressed Zarr

## Documentation

- **[HPC Deployment](docs/CRUX_DEPLOYMENT.md)**: Complete guide for supercomputer deployment
- **[Multi-frame Support](docs/MULTIFRAME_SUPPORT.md)**: Working with EDF and GE5 files
- **[File Structure](docs/FILESTRUCTURE.md)**: Understanding the data organization

## Authors

- **William Gonzalez** - Principal Developer
- **Adrian Guzman** - GUI Development, Visualization
- **Luke Davenport** - Data Analyzer GUI

## Citation

If you use PRISMA in your research, please cite (paper in progress):

```bibtex
@software{prisma2025,
  title = {PRISMA: Parallel Refinement and Integration System for Multi-Azimuthal Analysis},
  author = {Gonzalez, William and Guzman, Adrian and Davenport, Luke and Lorenzo-Martin, Cinta},
  year = {2025},
  version = {Beta 0.1},
  url = {https://github.com/wdgonzo/PRISMA}
}
```

## License

[To be determined - add appropriate license]

## Acknowledgments

- GSAS-II development team for the powerful crystallographic software
- ALCF Crux supercomputer for HPC testing and validation
- Materials science community for feedback and use cases

## Support

For issues, questions, or contributions:
- **Issues**: [GitHub Issues](https://github.com/wdgonzo/PRISMA/issues)
- **Documentation**: [Wiki](https://github.com/wdgonzo/PRISMA/wiki)
- **Contact**: [wgonzalez@anl.gov]

---

**PRISMA Beta 0.1** - October 2025
