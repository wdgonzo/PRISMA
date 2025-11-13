"""
PRISMA - Parallel Refinement and Integration System for Multi-Azimuthal Analysis
=================================================================================
A Python-based X-ray diffraction (XRD) data processing system for materials
science analysis.

Author(s): William Gonzalez, Adrian Guzman, Luke Davenport
Date: October 2025
Version: Beta 0.3
"""

__version__ = "0.3.0-beta"
__author__ = "William Gonzalez, Adrian Guzman, Luke Davenport"

# Core exports
from XRD.core.gsas_processing import XRDDataset, GSASParams, PeakParams, Stages
from XRD.core.image_loader import ImageLoader, ImageFrameInfo

# Processing exports
from XRD.processing.recipes import create_gsas_params_from_recipe, load_recipe_from_file

# Visualization exports
from XRD.visualization.data_visualization import create_visualization, GraphParams, GraphSetting

# HPC exports
from XRD.hpc.cluster import get_dask_client, close_dask_client

__all__ = [
    # Core
    'XRDDataset', 'GSASParams', 'PeakParams', 'Stages',
    'ImageLoader', 'ImageFrameInfo',
    # Processing
    'create_gsas_params_from_recipe', 'load_recipe_from_file',
    # Visualization
    'create_visualization', 'GraphParams', 'GraphSetting',
    # HPC
    'get_dask_client', 'close_dask_client',
]
