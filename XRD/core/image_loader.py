"""
Image Loader Module
===================
Provides unified interface for loading various X-ray diffraction image formats.
Supports single-frame (.tif) and multi-frame (.edf, .edf.GE5) files.

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import os
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import numpy as np

try:
    import fabio
    FABIO_AVAILABLE = True
except ImportError:
    FABIO_AVAILABLE = False
    print("Warning: FABIO not available. Multi-frame EDF/GE5 support disabled.")


@dataclass
class ImageFrameInfo:
    """Information about a single frame from an image file."""
    file_path: str          # Path to the source file
    frame_index: int        # Frame index within the file (0-based)
    file_frame_index: int   # Original frame number in multi-frame file
    is_multiframe: bool     # Whether source is multi-frame file
    metadata: Dict          # Frame-specific metadata (timestamps, etc.)


class ImageLoader:
    """
    Unified image loader for XRD data processing.

    Handles both single-frame (.tif) and multi-frame (.edf, .edf.GE5) files,
    providing a consistent interface for parallel processing.
    """

    SUPPORTED_SINGLE_FRAME = ['.tif', '.tiff']
    SUPPORTED_MULTI_FRAME = ['.edf', '.edf.ge5', '.edf.ge1', '.edf.ge2',
                             '.edf.ge3', '.edf.ge4']

    @classmethod
    def is_supported(cls, filepath: str) -> bool:
        """Check if file format is supported."""
        ext = cls._get_extension(filepath)
        return (ext in cls.SUPPORTED_SINGLE_FRAME or
                ext in cls.SUPPORTED_MULTI_FRAME)

    @classmethod
    def is_multiframe(cls, filepath: str) -> bool:
        """Check if file is a multi-frame format."""
        ext = cls._get_extension(filepath)
        return ext in cls.SUPPORTED_MULTI_FRAME

    @staticmethod
    def _get_extension(filepath: str) -> str:
        """Get file extension, handling compound extensions like .edf.GE5"""
        filename = os.path.basename(filepath).lower()

        # Check for compound extensions first
        for ext in ['.edf.ge5', '.edf.ge1', '.edf.ge2', '.edf.ge3', '.edf.ge4']:
            if filename.endswith(ext):
                return ext

        # Check for simple extensions
        _, ext = os.path.splitext(filename)
        return ext

    @classmethod
    def discover_frames(cls, directory: str,
                       start_frame: int = 0,
                       end_frame: int = -1,
                       step: int = 1) -> List[ImageFrameInfo]:
        """
        Discover all image frames in a directory.

        Handles both single-frame files and multi-frame files,
        returning a flat list of ImageFrameInfo objects.

        Args:
            directory: Directory to search for images
            start_frame: Starting frame index (global across all files)
            end_frame: Ending frame index (-1 for all frames)
            step: Frame sampling step

        Returns:
            List of ImageFrameInfo objects in sequential order
        """
        frames = []
        global_frame_index = 0

        # Get all files in directory
        all_files = []
        for root, dirs, files in os.walk(directory):
            for file in sorted(files):
                filepath = os.path.join(root, file)
                if cls.is_supported(filepath):
                    all_files.append(filepath)

        # Process each file
        for filepath in sorted(all_files):
            if cls.is_multiframe(filepath):
                # Multi-frame file: enumerate all frames
                frame_count = cls.get_frame_count(filepath)
                if frame_count is None:
                    print(f"Warning: Could not read frame count from {filepath}")
                    continue

                for file_frame_idx in range(frame_count):
                    # Check if this frame meets the criteria
                    if end_frame != -1 and global_frame_index >= end_frame:
                        break

                    if (global_frame_index >= start_frame and
                        global_frame_index % step == 0):

                        # Get metadata for this frame
                        metadata = cls.get_frame_metadata(filepath, file_frame_idx)

                        frames.append(ImageFrameInfo(
                            file_path=filepath,
                            frame_index=global_frame_index,
                            file_frame_index=file_frame_idx,
                            is_multiframe=True,
                            metadata=metadata
                        ))

                    global_frame_index += 1

                if end_frame != -1 and global_frame_index >= end_frame:
                    break
            else:
                # Single-frame file
                if end_frame != -1 and global_frame_index >= end_frame:
                    break

                if (global_frame_index >= start_frame and
                    global_frame_index % step == 0):

                    frames.append(ImageFrameInfo(
                        file_path=filepath,
                        frame_index=global_frame_index,
                        file_frame_index=0,
                        is_multiframe=False,
                        metadata={}
                    ))

                global_frame_index += 1

        return frames

    @staticmethod
    def get_frame_count(filepath: str) -> Optional[int]:
        """Get number of frames in a file."""
        if not FABIO_AVAILABLE:
            return None

        try:
            img = fabio.open(filepath)
            return img.nframes
        except Exception as e:
            print(f"Error reading frame count from {filepath}: {e}")
            return None

    @staticmethod
    def get_frame_metadata(filepath: str, frame_index: int = 0) -> Dict:
        """Get metadata for a specific frame."""
        if not FABIO_AVAILABLE:
            return {}

        try:
            img = fabio.open(filepath)
            frame = img.getframe(frame_index)
            return dict(frame.header) if hasattr(frame, 'header') else {}
        except Exception as e:
            print(f"Error reading metadata from {filepath} frame {frame_index}: {e}")
            return {}

    @staticmethod
    def extract_frame_to_tif(frame_info: ImageFrameInfo,
                            output_path: str) -> bool:
        """
        Extract a specific frame and save as .tif file.

        Args:
            frame_info: Frame information
            output_path: Path to save the .tif file

        Returns:
            True if successful, False otherwise
        """
        if not FABIO_AVAILABLE:
            print("Error: FABIO not available for frame extraction")
            return False

        try:
            # Load the frame
            img = fabio.open(frame_info.file_path)

            if frame_info.is_multiframe:
                frame = img.getframe(frame_info.file_frame_index)
            else:
                frame = img

            # Save as TIF
            tif_img = fabio.tifimage.TifImage(data=frame.data, header=frame.header)
            tif_img.write(output_path)

            return True

        except Exception as e:
            print(f"Error extracting frame: {e}")
            return False

    @staticmethod
    def load_frame_data(frame_info: ImageFrameInfo) -> Optional[np.ndarray]:
        """
        Load frame data as NumPy array.

        Args:
            frame_info: Frame information

        Returns:
            NumPy array of image data, or None on error
        """
        if not FABIO_AVAILABLE:
            print("Error: FABIO not available for frame loading")
            return None

        try:
            img = fabio.open(frame_info.file_path)

            if frame_info.is_multiframe:
                frame = img.getframe(frame_info.file_frame_index)
            else:
                frame = img

            return frame.data

        except Exception as e:
            print(f"Error loading frame data: {e}")
            return None


def validate_frame_ordering(frames: List[ImageFrameInfo]) -> bool:
    """
    Validate that frames are in correct sequential order.

    Args:
        frames: List of ImageFrameInfo objects

    Returns:
        True if ordering is valid
    """
    if not frames:
        return True

    # Check that frame_index increases monotonically
    for i in range(1, len(frames)):
        if frames[i].frame_index <= frames[i-1].frame_index:
            print(f"Warning: Frame ordering issue at index {i}")
            print(f"  Frame {i-1}: {frames[i-1].frame_index}")
            print(f"  Frame {i}: {frames[i].frame_index}")
            return False

    # Check for metadata timestamps if available
    timestamps = []
    for frame in frames:
        if 'timestamp' in frame.metadata or 'DATE' in frame.metadata:
            ts = frame.metadata.get('timestamp') or frame.metadata.get('DATE')
            timestamps.append(ts)

    if timestamps and len(timestamps) == len(frames):
        print(f"Frame ordering validated with {len(timestamps)} timestamps")

    return True


# Utility function for backward compatibility
def get_image_files(directory: str, start_frame: int = 0,
                   end_frame: int = -1, step: int = 1) -> List[str]:
    """
    Get list of image files (backward compatible with old .tif-only code).

    For multi-frame files, returns the filepath repeated for each frame.
    """
    frames = ImageLoader.discover_frames(directory, start_frame, end_frame, step)
    return [frame.file_path for frame in frames]
