"""
Utility Functions Module
========================
General utility functions and helpers for XRD processing.

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import functools
import numpy as np
from typing import List, Dict, Any, Union, Optional
from dataclasses import dataclass
from tqdm import tqdm

@dataclass
class ProcessingConfig:
    """Configuration for processing parameters"""
    max_iterations: int = 10
    convergence_threshold: float = 1e-6
    outlier_threshold: float = 1.5
    cache_size: int = 128

@functools.lru_cache(maxsize=128)
def calculate_d_spacing(two_theta: float, wavelength: float) -> float:
    """
    Calculate d-spacing using Bragg's law with caching
    """
    return wavelength / (2 * np.sin(np.radians(two_theta / 2)))

def detect_outliers(data: np.ndarray, threshold: float = 1.5) -> np.ndarray:
    """
    Detect outliers using IQR method
    """
    q1 = np.percentile(data, 25)
    q3 = np.percentile(data, 75)
    iqr = q3 - q1
    lower_bound = q1 - threshold * iqr
    upper_bound = q3 + threshold * iqr
    return (data >= lower_bound) & (data <= upper_bound)

def validate_input_parameters(params: dict) -> bool:
    """
    Validate input parameters
    """
    required_params = ['sample', 'spacing', 'azimuths']
    return all(param in params for param in required_params)

def export_results(data: Any, format: str = 'csv') -> None:
    """
    Export results in various formats
    """
    supported_formats = ['csv', 'json', 'xlsx']
    if format not in supported_formats:
        raise ValueError(f"Unsupported format. Choose from {supported_formats}")
    
    # Implementation for different formats
    pass

def calculate_peak_quality_metrics(peak_data: np.ndarray) -> Dict[str, float]:
    """
    Calculate quality metrics for peak fitting
    """
    metrics = {
        'r_squared': 0.0,
        'chi_squared': 0.0,
        'residual_std': 0.0,
        'signal_to_noise': 0.0
    }
    
    # Implementation of metrics calculation
    return metrics
