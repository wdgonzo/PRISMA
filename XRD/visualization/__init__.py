"""
Visualization module - Data visualization and plotting
======================================================

Author(s): William Gonzalez, Adrian Guzman
Date: October 2025
Version: Beta 0.1
"""

from XRD.visualization.data_visualization import (
    create_visualization,
    create_visualizations_from_datasets,
    GraphParams,
    GraphSetting
)
from XRD.visualization.plotting import (
    prepare_heatmap_data,
    draw_heatmap,
    create_heatmap_plot,
    configure_plot_appearance,
    load_cof_data,
    save_figure
)

__all__ = [
    # Main visualization
    'create_visualization',
    'create_visualizations_from_datasets',
    'GraphParams',
    'GraphSetting',
    # Plotting functions
    'prepare_heatmap_data',
    'draw_heatmap',
    'create_heatmap_plot',
    'configure_plot_appearance',
    'load_cof_data',
    'save_figure',
]
