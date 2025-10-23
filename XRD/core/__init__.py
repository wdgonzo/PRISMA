"""
Core module - Data structures and GSAS-II integration
=====================================================

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

from XRD.core.gsas_processing import (
    XRDDataset,
    GSASParams,
    PeakParams,
    Stages,
    process_images,
    load_or_process_data,
    subtract_datasets
)
from XRD.core.image_loader import (
    ImageLoader,
    ImageFrameInfo,
    validate_frame_ordering
)

__all__ = [
    'XRDDataset',
    'GSASParams',
    'PeakParams',
    'Stages',
    'process_images',
    'load_or_process_data',
    'subtract_datasets',
    'ImageLoader',
    'ImageFrameInfo',
    'validate_frame_ordering',
]
