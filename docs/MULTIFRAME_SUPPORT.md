# Multi-Frame Image Support (EDF/GE5)

## Overview
The XRD Processor now supports multi-frame image formats including `.edf` and `.edf.GE5` files in addition to the original `.tif` format. This allows processing of large datasets stored in single container files (e.g., 1400 images in one `.edf.GE5` file).

## Supported Formats

### Single-Frame Formats
- `.tif`, `.tiff` - TIFF image files (original support)

### Multi-Frame Formats (NEW)
- `.edf` - European Data Format
- `.edf.GE5` - GE detector format variant 5
- `.edf.GE1`, `.edf.GE2`, `.edf.GE3`, `.edf.GE4` - Other GE variants

## How It Works

### Frame Discovery
The new `ImageLoader` class automatically:
1. Scans directories for supported image files
2. Detects multi-frame files and enumerates internal frames
3. Returns a flat list of frame information maintaining sequential order
4. Validates frame ordering using metadata timestamps when available

### Parallel Processing
Multi-frame support integrates seamlessly with the existing parallel processing:
- Each worker process accesses only its assigned frame from the multi-frame file
- Frames are extracted to temporary `.tif` files on-demand
- Temporary files are automatically cleaned up after processing
- Memory efficient: only one frame loaded per worker at a time

### Frame Ordering
Frame order is preserved through:
- Sequential frame indices within multi-frame files (0, 1, 2, ..., N-1)
- Global frame numbering across all files in a directory
- Metadata validation (timestamps, scan numbers) when available
- Explicit logging of frame provenance during processing

## Usage

### No Code Changes Required
If you're using the GUI (recipe_builder.py), **no changes are needed**:
1. Select your image folder as usual (Browse button)
2. The system automatically detects `.edf.GE5` or other multi-frame files
3. Processing proceeds normally with all frames discovered automatically

### Example: Processing a GE5 Dataset
```
Directory structure:
/my_experiment/
├── Images/
│   └── my_sample/
│       └── dataset.edf.GE5  (contains 1400 frames)
└── Refs/
    └── my_setting/
        └── reference.edf.GE5  (contains 10 frames)
```

When you:
1. Set "Images" folder to `/my_experiment/Images/my_sample/`
2. Set "Refs" folder to `/my_experiment/Refs/my_setting/`
3. Set frame range [0, 1400] and step=1

The system will:
- Discover 1400 frames in the GE5 file
- Process frames 0-1399 in parallel
- Maintain correct temporal/depth ordering
- Generate the same XRD dataset structure as with 1400 `.tif` files

### Frame Range and Sampling
The frame parameters work identically:
- `start_frame`: First frame to process (global index across all files)
- `end_frame`: Last frame to process (-1 for all frames)
- `step`: Sample every Nth frame

Example with multi-frame file:
```json
{
  "frames": [0, -1],  // Process all frames
  "step": 10          // Every 10th frame
}
```
This will process frames 0, 10, 20, 30, ... from the multi-frame file.

## Installation

### Required Dependency
The multi-frame support requires the FABIO library:
```bash
pip install fabio
```

Or run the updated initialization:
```bash
python XRD/initialize.py
```

### Verification
To verify FABIO is installed:
```python
python -c "import fabio; print(f'FABIO version: {fabio.version}')"
```

If FABIO is not available, the system will:
- Issue a warning at startup
- Fall back to `.tif`-only support
- Continue working for single-frame `.tif` files

## Technical Details

### Architecture
- **Module**: `XRD/image_loader.py` - Unified image loading interface
- **Integration**: `XRD/gsas_processing.py` - Uses ImageLoader for frame discovery
- **Extraction**: Temporary `.tif` files created on-demand per worker
- **Cleanup**: Automatic removal of temporary files after processing

### Performance
- **Memory**: No increase vs `.tif` files (one frame per worker)
- **Speed**: ~5-10% overhead for frame extraction (negligible vs GSAS processing time)
- **Storage**: Multi-frame files remain on disk, temps are cleaned up immediately
- **Parallelization**: Full parallel efficiency maintained

### Frame Metadata
Each frame includes:
- `file_path`: Source file containing the frame
- `frame_index`: Global sequential index in dataset
- `file_frame_index`: Frame number within the multi-frame file
- `metadata`: Header information (timestamps, scan parameters, etc.)

Metadata logging example:
```
Frame 142 (file frame 142): Mon Jun 28 21:22:16 2010
Frame 143 (file frame 143): Mon Jun 28 21:22:17 2010
```

## Troubleshooting

### "No reference images found" or "No sample images found"
- Check that FABIO is installed: `pip install fabio`
- Verify file extensions are recognized (`.edf`, `.edf.GE5`, etc.)
- Check file permissions and accessibility

### "Warning: Frame ordering may be incorrect"
- This occurs if frame indices are non-sequential
- Usually safe to ignore if you know your data is ordered correctly
- Check frame metadata timestamps for validation

### "Warning: Failed to extract frame N"
- FABIO could not read the specific frame
- Possible file corruption or format incompatibility
- The system will attempt to continue with remaining frames

### Performance Issues
If extraction is slow:
- Ensure files are on fast storage (SSD preferred)
- Check available disk space for temporary files (TEMP directory)
- Consider pre-extracting frames if processing multiple times:
  ```python
  # One-time extraction script
  from XRD.image_loader import ImageLoader
  import fabio

  img = fabio.open("dataset.edf.GE5")
  for i in range(img.nframes):
      frame_data = img.getframe(i).data
      fabio.tifimage.TifImage(data=frame_data).save(f"extracted/frame_{i:04d}.tif")
  ```

## Backward Compatibility

### Existing Workflows
All existing `.tif`-based workflows continue to work without changes:
- Old recipe files work as-is
- `.tif` files are processed identically
- No changes to output format or data structure

### Mixed Formats
You can have both `.tif` and `.edf.GE5` files in the same directory:
- The ImageLoader discovers all supported formats
- Frames are sequenced in alphabetical filename order, then by internal frame index
- Not recommended due to potential ordering ambiguity

## Future Enhancements

Potential improvements:
- [ ] Direct GSAS-II multi-frame support (avoid temp file extraction)
- [ ] HDF5/NeXus format support
- [ ] Parallel frame extraction pipeline
- [ ] Frame metadata export to dataset attributes

## References

- FABIO Documentation: https://www.silx.org/doc/fabio/
- GSAS-II EDF Support: https://gsas-ii.readthedocs.io/en/latest/imports.html
- European Data Format Specification: https://www.esrf.eu/computing/scientific/FIT2D/FIT2D_REF/node115.html
