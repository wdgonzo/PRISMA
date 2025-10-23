"""
Processing module - Data generation and workflow management
===========================================================

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

from XRD.processing.data_generator import main as generate_data
from XRD.processing.batch_processor import main as batch_process
from XRD.processing.recipes import (
    create_gsas_params_from_recipe,
    load_recipe_from_file
)

__all__ = [
    'generate_data',
    'batch_process',
    'create_gsas_params_from_recipe',
    'load_recipe_from_file',
]
