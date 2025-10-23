# XRD Processor File Structure

This document describes the complete file organization structure for the XRD data processing system.

## Overview

The system uses a centralized, hierarchical directory structure organized by data type, date, and sample. All paths are relative to a configurable **Home Directory**.

## Directory Tree

```
Home/  (configurable root directory)
├── [User's Data]/      # Raw experimental data (user-specified location)
│   ├── Images/         # Raw diffraction images (.tif, .edf, .edf.GE5)
│   └── Refs/           # Reference images for strain calculation (optional)
│
├── Processed/          # Processed datasets
│   └── {DateStamp}/    # Processing date (YYYY-MM-DD format)
│       └── {Sample}/   # Sample identifier
│           ├── Zarr/   # Processed XRD datasets (Zarr format)
│           │   └── {ParamsString}/  # Parameter-encoded folder name
│           │       ├── data.zarr/
│           │       ├── frame_numbers.zarr/
│           │       ├── azimuth_angles.zarr/
│           │       └── metadata.json
│           └── Intensity/  # Raw intensity plots for ML/analysis
│               └── {ParamsString}/  # Per-peak parameter folder
│                   ├── Frame0000/
│                   │   ├── az_0.tiff
│                   │   ├── az_5.tiff
│                   │   └── ...
│                   └── Frame0001/
│                       └── ...
│
├── Analysis/           # Analysis outputs (plots, CSVs)
│   └── {DateStamp}/    # Analysis date (YYYY-MM-DD format)
│       └── {Sample}/   # Sample identifier
│           ├── {AnalysisFile1}.tiff  # Heatmap visualizations
│           ├── {AnalysisFile1}.csv   # Corresponding data
│           ├── {AnalysisFile2}.tiff
│           ├── {AnalysisFile2}.csv
│           └── analysis_metadata.json  # Links to source datasets
│
└── Params/             # Configuration and parameter files
    ├── recipes/        # Processing recipes (JSON)
    │   ├── processed/  # Archive of processed recipes
    │   └── {RecipeFile}.json
    └── analyzer/       # Analyzer configuration files
        └── {AnalysisParams}.json
```

## Naming Conventions

### Zarr Folder Names

Zarr folders use descriptive parameter strings with identifiers to encode processing settings:

**Format**: `{total}deg-{bins}bins-{start}sf-{end}efr-{lower}l2t_{upper}u2t-{npeaks}peaks-{nbkg}bkg-{time}`

**Example**: `360deg-72bins-0sf-100efr-8.2l2t_8.8u2t-3peaks-2bkg-143022`

**Breakdown**:
- `360deg` = Total azimuthal range (360 degrees)
- `72bins` = Number of azimuthal bins (72)
- `0sf` = Starting frame (sf = start frame)
- `100efr` = Ending frame (efr = end frame; use `allfr` for -1)
- `8.2l2t` = Lower 2θ limit (l2t = lower 2-theta)
- `8.8u2t` = Upper 2θ limit (u2t = upper 2-theta)
- `3peaks` = Number of peaks analyzed
- `2bkg` = Number of background peaks
- `143022` = Processing timestamp (HHMMSS format, time only)

### Intensity Folder Names

Intensity plot folders are dataset-level (not per-peak) with identifiers:

**Format**: `{total}deg-{bins}bins-{start}sf-{end}efr-{lower}l2t_{upper}u2t-{time}`

**Example**: `360deg-72bins-0sf-100efr-8.2l2t_8.8u2t-143022`

**Breakdown**:
- `360deg` = Total azimuthal range (360 degrees)
- `72bins` = Number of azimuthal bins (72)
- `0sf` = Starting frame (sf = start frame)
- `100efr` = Ending frame (efr = end frame; use `allfr` for -1)
- `8.2l2t` = Lower 2θ limit (l2t = lower 2-theta)
- `8.8u2t` = Upper 2θ limit (u2t = upper 2-theta)
- `143022` = Processing timestamp (HHMMSS format)
- **Note**: No peak identifier - intensity plots are dataset-level

### Analysis File Names

Analysis files (plots/CSVs) use detailed descriptive names with identifiers and dataset traceability:

**Format**: `{peakname}{miller}-{mode}-{colormap}-[{lower}l2t_{upper}u2t]-{frames}-DS{id}-{time}.{ext}`

**Example**: `Martensite211-RobustLL-Viridis-8.2l2t_8.8u2t-F50_100-DSa1b2c3d4-143022.tiff`

**Breakdown**:
- `Martensite211` = Peak name + Miller index
- `RobustLL` = Graphing mode (Standard, Robust, RobustLL, StandardLL)
- `Viridis` = Color map used
- `8.2l2t_8.8u2t` = 2θ limits when using locked limits mode (optional, only with LL modes)
- `F50_100` = Frame range (ALWAYS included; use `allfr` for all frames or F{start}_{end} for specific range)
- `DSa1b2c3d4` = Dataset ID (8-character hash linking to source Zarr)
- `143022` = Analysis timestamp (HHMMSS format, time only)
- `.tiff` = File extension (also .csv for data)

**Note**: Analysis filenames always include frame information and use 2θ limits (not strain limits) when applicable.

### Recipe File Names

Recipe files encode sample, settings, and peaks:

**Format**: `{Sample}_{Setting}_{Stage}_{Peaks}_{Timestamp}.json`

**Example**: `A1_Standard_CONT_211_20251022_143022.json`

## Data Flow

### 1. Data Collection

Raw diffraction images can be organized anywhere on your system. The user explicitly specifies paths to their data:

```
/any/path/to/experimental/data/Images/
├── image_0000.tif
├── image_0001.tif
└── ...
```

Reference images for strain calculation (optional):

```
/any/path/to/experimental/data/Refs/
├── ref_0000.tif
└── ref_0001.tif
```

**Note**: References are optional. If not provided, strain calculation will be skipped.

### 2. Recipe Creation

Using `recipe_builder.py`:
1. Set **Home Directory** (for outputs only)
2. Set **Images Directory** (explicit path to your images)
3. Set **References Directory** (explicit path to refs, or leave empty)
4. Check "No reference images" if strain calculation not needed
5. Configure sample, peaks, and processing parameters
6. Recipe saved to: `{Home}/Params/recipes/{RecipeFile}.json`

### 3. Data Processing

Using `batch_processor.py`:
1. Reads recipes from `{Home}/Params/recipes/`
2. Processes diffraction images through GSAS-II
3. Saves Zarr datasets to: `{Home}/Processed/{Date}/{Sample}/Zarr/{Params}/`
4. Saves intensity plots to: `{Home}/Processed/{Date}/{Sample}/Intensity/{Params}/`
5. Moves processed recipe to: `{Home}/Params/recipes/processed/`

### 4. Analysis & Visualization

Using `data_analyzer.py` or `visualization_interface.py`:
1. Scans `{Home}/Processed/{Date}/{Sample}/Zarr/` for datasets
2. Loads selected Zarr dataset
3. Generates heatmap visualizations
4. Saves plots/CSVs to: `{Home}/Analysis/{Date}/{Sample}/{AnalysisFile}`
5. Updates `analysis_metadata.json` with dataset lineage

## Dataset Traceability

### Dataset IDs

Each processed dataset gets a unique 8-character ID (MD5 hash of parameters):
- Enables linking analysis outputs back to source data
- Included in analysis filenames (e.g., `DSa1b2c3d4`)
- Tracked in `analysis_metadata.json`

### Metadata Files

#### `metadata.json` (in Zarr folders)

Stores dataset parameters and structure information:
```json
{
  "n_peaks": 3,
  "n_frames": 100,
  "n_azimuths": 44,
  "measurement_cols": ["d-spacing", "strain", "area", "width"],
  "col_idx": {"d-spacing": 0, "strain": 1, ...},
  "peak_miller_indices": [110, 200, 211],
  "created": "2025-10-22T14:30:22",
  "params": {...}
}
```

#### `analysis_metadata.json` (in Analysis folders)

Links analysis outputs to source datasets:
```json
{
  "created": "2025-10-22T15:45:00",
  "datasets": {
    "a1b2c3d4": {
      "zarr_path": "/.../Processed/2025-10-22/A1/Zarr/360deg-72bins-0sf-100efr-8.2l2t_8.8u2t-3peaks-2bkg-143022/",
      "first_used": "2025-10-22T15:45:00"
    }
  },
  "analyses": [
    {
      "file": "Martensite211-RobustLL-Viridis-8.2l2t_8.8u2t-F50_100-DSa1b2c3d4-154530.tiff",
      "dataset_id": "a1b2c3d4",
      "created": "2025-10-22T15:45:30"
    }
  ]
}
```

## Path Management

All path generation is centralized in `XRD/path_manager.py`:

### Key Functions

- `get_data_path()` - Raw data directory
- `get_images_path()` - Raw images location
- `get_refs_path()` - Reference images location
- `get_zarr_path()` - Processed Zarr storage
- `get_intensity_path()` - Intensity plot storage
- `get_analysis_path()` - Analysis output location
- `get_recipes_path()` - Recipe file storage
- `find_zarr_datasets()` - Scan for processed datasets

### Path Generation Examples

```python
from path_manager import *

# Get paths
home = "/path/to/project"
data_path = get_data_path(home, "Oct2025", "A1", "CONT")
# Returns: /path/to/project/Data/Oct2025/A1/CONT

# Generate parameter strings with identifiers
zarr_params = generate_zarr_params_string(
    total_az=360, bin_count=72,
    frame_start=0, frame_end=100,
    theta_limits=(8.2, 8.8),
    num_peaks=3, num_bkg=2,
    timestamp=None
)
# Returns: 360deg-72bins-0sf-100efr-8.2l2t_8.8u2t-3peaks-2bkg-143022

# Get full Zarr path
zarr_path = get_zarr_path(home, "A1", zarr_params)
# Returns: /path/to/project/Processed/2025-10-22/A1/Zarr/360deg-72bins-0sf-100efr-8.2l2t_8.8u2t-3peaks-2bkg-143022

# Generate analysis filename with identifiers
filename = generate_analysis_filename(
    peak_name="Martensite", peak_miller="211",
    graph_mode="RobustLL", color_mode="Viridis",
    locked_lims=(8.2, 8.8),  # 2θ limits, not strain
    frame_range=(50, 100),
    dataset_id="a1b2c3d4"
)
# Returns: Martensite211-RobustLL-Viridis-8.2l2t_8.8u2t-F50_100-DSa1b2c3d4-143022.tiff
```

## Benefits of This Structure

### 1. **Organization by Purpose**
- Raw data: User-specified location (any structure)
- Processed data in `Processed/`
- Analysis results in `Analysis/`
- Configuration in `Params/`

### 2. **Flexibility**
- Works with ANY directory structure for raw data
- No assumptions about how you organize experiments
- Optional references for datasets without strain analysis

### 2. **Chronological Organization**
- Date stamps enable easy historical tracking
- Multiple processing runs don't overwrite each other

### 3. **Self-Documenting Filenames**
- Parameter strings encode processing settings
- No need to open files to understand what's inside

### 4. **Traceability**
- Dataset IDs link analysis back to source data
- Metadata files track data lineage
- Can reproduce any analysis from the source Zarr

### 5. **Separation of Processed Data Types**
- Zarr datasets: Complete 4D data structure
- Intensity plots: Individual 2θ patterns for ML/inspection
- Analysis outputs: Final visualizations separate from raw processing

### 6. **No Overwrites**
- Timestamps ensure uniqueness
- Multiple analyses of same data coexist
- Historical data preserved

### 7. **Scalability**
- Works for single samples or hundreds
- Date-based organization prevents folder bloat
- Easy to archive old data by date

## Migration from Old Structure

### Old Structure (Pre-v2.0)

```
ImageFolder/
├── Images/
├── Refs/
├── Processed_Data/
│   └── {DateFolder}/
│       └── {LongFilename}_timestamp/
└── IntensityPlots/
```

### Migration Steps

1. **No automatic migration** - new structure only applies to new data
2. **Old data remains accessible** - load functions attempt to read old formats
3. **Best practice**: Reprocess old data with new recipes to standardize structure

## Configuration

### Setting Home Directory

#### In Recipe Builder:
1. Open `recipe_builder.py`
2. Set "Home Directory" field at top
3. All subsequent paths relative to this directory

#### In Analysis Tools:
1. Open `data_analyzer.py` or `visualization_interface.py`
2. Set "Home Directory" in interface
3. Scans for datasets in `{Home}/Processed/`

### Default Behavior

If home directory not specified:
- Defaults to current working directory
- Uses relative paths from execution location

## Technical Notes

### Date Format

- **Date stamps**: `YYYY-MM-DD` (e.g., "2025-10-22") - Used for directory organization
- **Time stamps**: `HHMMSS` (e.g., "143022") - Used in filenames (time only, no date)
- **Full timestamps**: `YYYY-MM-DD_HHMMSS` (e.g., "2025-10-22_143022") - Used in recipe filenames only
- **Month-Year**: `MonYYYY` (e.g., "Oct2025") - Legacy format, not used in new structure

### Filename Identifiers

All values in filenames include descriptive identifiers (units AFTER values):
- **deg** = degrees (e.g., `360deg` = 360 degrees)
- **bins** = azimuthal bins (e.g., `72bins` = 72 bins)
- **sf** = start frame (e.g., `0sf` = frame 0)
- **efr** = end frame (e.g., `100efr` = frame 100; `allfr` = all frames / -1)
- **l2t** = lower 2θ limit (e.g., `8.2l2t` = 8.2° 2θ)
- **u2t** = upper 2θ limit (e.g., `8.8u2t` = 8.8° 2θ)
- **peaks** = number of peaks (e.g., `3peaks` = 3 peaks)
- **bkg** = background peaks (e.g., `2bkg` = 2 background peaks)
- **F** prefix = frame range in analysis files (e.g., `F50_100` = frames 50-100)
- **DS** prefix = dataset ID (e.g., `DSa1b2c3d4` = dataset a1b2c3d4)

### Negative Number Encoding

Negative numbers in filenames use "minus" prefix (rarely used with new identifier system):
- `-110` becomes `minus110`
- `-90` becomes `minus90`
- Positive numbers unchanged: `110` stays `110`

### File Extensions

- **Diffraction images**: `.tif`, `.edf`, `.edf.GE5`
- **Analysis plots**: `.tiff` (high-quality output)
- **Data exports**: `.csv`
- **Configuration**: `.json`
- **Masks**: `.immask`
- **Calibration**: `.imctrl`

## Version History

- **v2.0** (October 2025): Reorganized file structure with centralized path management
- **v1.x** (Pre-October 2025): Original flat structure with mixed organization

## See Also

- `XRD/path_manager.py` - Path generation implementation
- `CLAUDE.md` - Development guidelines and project overview
- Recipe Builder GUI - Visual interface for creating processing recipes
- Data Analyzer GUI - Visual interface for dataset analysis
