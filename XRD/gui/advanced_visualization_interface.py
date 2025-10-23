#!/usr/bin/env python3
"""
Advanced XRD Data Visualization Interface
==========================================
Enhanced GUI interface for comprehensive XRD data visualization with:
- Tabbed multi-analysis system
- Dynamic peak management with metadata
- Persistent image gallery with grid/carousel views
- Real-time preview with smart throttling
- Delta/difference calculations integration
- Unique timestamp-based filename generation

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QWidget, QFileDialog, QLineEdit, QComboBox, QCheckBox, QMessageBox, QGridLayout,
    QListWidget, QListWidgetItem, QSplitter, QTextEdit, QGroupBox, QSpinBox,
    QTabWidget, QScrollArea, QFrame, QSlider, QDoubleSpinBox, QTreeWidget,
    QTreeWidgetItem, QProgressBar, QToolButton, QMenu, QAction, QButtonGroup,
    QRadioButton, QTableWidget, QTableWidgetItem
)
from PyQt5 import QtGui, QtCore
from PyQt5.QtGui import QCursor, QPixmap, QIcon, QFont, QPalette, QColor
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
import json
import os
import sys
import glob
from datetime import datetime
import uuid
import threading
import time

# Import visualization components
from XRD.visualization import data_visualization
from XRD.core.gsas_processing import XRDDataset, Stages, PeakConfig


class ImageGalleryWidget(QWidget):
    """Enhanced image gallery with grid view and carousel functionality."""

    imageClicked = pyqtSignal(str)  # Signal when image is clicked

    def __init__(self):
        super().__init__()
        self.images = []  # List of image metadata
        self.current_view = "grid"  # "grid" or "carousel"
        self.current_index = 0
        self.init_ui()

    def init_ui(self):
        """Initialize the image gallery UI."""
        layout = QVBoxLayout(self)

        # Gallery controls
        controls_layout = QHBoxLayout()

        # View mode buttons
        self.grid_btn = QPushButton("Grid View")
        self.grid_btn.setCheckable(True)
        self.grid_btn.setChecked(True)
        self.grid_btn.clicked.connect(lambda: self.set_view_mode("grid"))

        self.carousel_btn = QPushButton("Carousel View")
        self.carousel_btn.setCheckable(True)
        self.carousel_btn.clicked.connect(lambda: self.set_view_mode("carousel"))

        view_group = QButtonGroup()
        view_group.addButton(self.grid_btn)
        view_group.addButton(self.carousel_btn)

        controls_layout.addWidget(self.grid_btn)
        controls_layout.addWidget(self.carousel_btn)
        controls_layout.addStretch()

        # Clear gallery button
        clear_btn = QPushButton("Clear Gallery")
        clear_btn.clicked.connect(self.clear_gallery)
        controls_layout.addWidget(clear_btn)

        layout.addLayout(controls_layout)

        # Stacked widget for different views
        self.view_stack = QWidget()
        self.view_layout = QVBoxLayout(self.view_stack)

        # Grid view
        self.grid_widget = QScrollArea()
        self.grid_content = QWidget()
        self.grid_layout = QGridLayout(self.grid_content)
        self.grid_widget.setWidget(self.grid_content)
        self.grid_widget.setWidgetResizable(True)

        # Carousel view
        self.carousel_widget = QWidget()
        carousel_layout = QVBoxLayout(self.carousel_widget)

        # Carousel navigation
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.clicked.connect(self.previous_image)
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self.next_image)

        nav_layout.addWidget(self.prev_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_btn)
        carousel_layout.addLayout(nav_layout)

        # Current image display
        self.current_image_label = QLabel("No image selected")
        self.current_image_label.setAlignment(Qt.AlignCenter)
        self.current_image_label.setMinimumHeight(400)
        self.current_image_label.setStyleSheet("border: 1px solid #cccccc; background-color: white;")
        carousel_layout.addWidget(self.current_image_label)

        # Image info
        self.image_info_text = QTextEdit()
        self.image_info_text.setMaximumHeight(100)
        self.image_info_text.setReadOnly(True)
        carousel_layout.addWidget(self.image_info_text)

        # Initially show grid view
        self.view_layout.addWidget(self.grid_widget)
        layout.addWidget(self.view_stack)

    def set_view_mode(self, mode):
        """Switch between grid and carousel view modes."""
        if mode == self.current_view:
            return

        # Clear current view
        for i in reversed(range(self.view_layout.count())):
            self.view_layout.itemAt(i).widget().setParent(None)

        self.current_view = mode

        if mode == "grid":
            self.view_layout.addWidget(self.grid_widget)
            self.grid_btn.setChecked(True)
            self.carousel_btn.setChecked(False)
        else:  # carousel
            self.view_layout.addWidget(self.carousel_widget)
            self.grid_btn.setChecked(False)
            self.carousel_btn.setChecked(True)
            self.update_carousel_display()

    def add_image(self, image_path, metadata):
        """Add an image to the gallery."""
        image_info = {
            "path": image_path,
            "metadata": metadata,
            "timestamp": datetime.now(),
            "id": str(uuid.uuid4())[:8]
        }
        self.images.append(image_info)

        # Add to grid view
        self.add_to_grid(image_info)

        # Update carousel if active
        if self.current_view == "carousel":
            self.update_carousel_display()

    def add_to_grid(self, image_info):
        """Add image thumbnail to grid view."""
        # Calculate grid position
        row = len(self.images) // 3
        col = (len(self.images) - 1) % 3

        # Create thumbnail frame
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setMaximumSize(200, 250)
        frame_layout = QVBoxLayout(frame)

        # Image thumbnail
        try:
            pixmap = QPixmap(image_info["path"])
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                image_label = QLabel()
                image_label.setPixmap(scaled_pixmap)
                image_label.setAlignment(Qt.AlignCenter)
                image_label.mousePressEvent = lambda event, path=image_info["path"]: self.imageClicked.emit(path)
                frame_layout.addWidget(image_label)
        except Exception as e:
            # Fallback for loading issues
            placeholder = QLabel("Image Error")
            placeholder.setAlignment(Qt.AlignCenter)
            frame_layout.addWidget(placeholder)

        # Image info
        info_text = f"{image_info['metadata'].get('peak_name', 'Unknown Peak')}\n"
        info_text += f"{image_info['metadata'].get('map_type', 'Unknown')}\n"
        info_text += f"{image_info['timestamp'].strftime('%H:%M:%S')}"

        info_label = QLabel(info_text)
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 8pt; color: black;")
        frame_layout.addWidget(info_label)

        self.grid_layout.addWidget(frame, row, col)

    def update_carousel_display(self):
        """Update the carousel view with current image."""
        if not self.images:
            self.current_image_label.setText("No images available")
            self.image_info_text.clear()
            return

        if self.current_index >= len(self.images):
            self.current_index = 0

        current_image = self.images[self.current_index]

        # Load and display image
        try:
            pixmap = QPixmap(current_image["path"])
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(600, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.current_image_label.setPixmap(scaled_pixmap)
        except Exception:
            self.current_image_label.setText("Failed to load image")

        # Update info
        info = f"Image {self.current_index + 1} of {len(self.images)}\n"
        info += f"Peak: {current_image['metadata'].get('peak_name', 'Unknown')}\n"
        info += f"Map Type: {current_image['metadata'].get('map_type', 'Unknown')}\n"
        info += f"Generated: {current_image['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n"
        info += f"File: {os.path.basename(current_image['path'])}"

        self.image_info_text.setText(info)

        # Update navigation buttons
        self.prev_btn.setEnabled(len(self.images) > 1)
        self.next_btn.setEnabled(len(self.images) > 1)

    def previous_image(self):
        """Navigate to previous image in carousel."""
        if self.images:
            self.current_index = (self.current_index - 1) % len(self.images)
            self.update_carousel_display()

    def next_image(self):
        """Navigate to next image in carousel."""
        if self.images:
            self.current_index = (self.current_index + 1) % len(self.images)
            self.update_carousel_display()

    def clear_gallery(self):
        """Clear all images from the gallery."""
        reply = QMessageBox.question(self, "Clear Gallery",
                                   "Are you sure you want to clear all images from the gallery?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.images.clear()
            self.current_index = 0

            # Clear grid
            for i in reversed(range(self.grid_layout.count())):
                self.grid_layout.itemAt(i).widget().setParent(None)

            # Update carousel
            if self.current_view == "carousel":
                self.update_carousel_display()


class AnalysisTabWidget(QWidget):
    """Individual analysis tab with parameters and controls."""

    generateRequested = pyqtSignal(dict, str)  # Signal to generate visualization
    previewRequested = pyqtSignal(dict, str)   # Signal for preview

    def __init__(self, tab_name="Analysis", dataset=None):
        super().__init__()
        self.tab_name = tab_name
        self.dataset = dataset
        self.peak_controls = {}
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.request_preview)
        self.init_ui()

    def init_ui(self):
        """Initialize the analysis tab UI."""
        layout = QVBoxLayout(self)

        # Tab name and controls
        header_layout = QHBoxLayout()

        name_label = QLabel("Analysis Name:")
        self.name_entry = QLineEdit(self.tab_name)
        self.name_entry.textChanged.connect(self.on_parameter_changed)

        header_layout.addWidget(name_label)
        header_layout.addWidget(self.name_entry)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Scroll area for parameters
        scroll = QScrollArea()
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Basic parameters
        basic_group = self.create_basic_parameters_group()
        scroll_layout.addWidget(basic_group)

        # Peak-specific parameters
        peaks_group = self.create_peak_parameters_group()
        scroll_layout.addWidget(peaks_group)

        # Advanced options
        advanced_group = self.create_advanced_options_group()
        scroll_layout.addWidget(advanced_group)

        scroll.setWidget(scroll_content)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        # Action buttons
        buttons_layout = QHBoxLayout()

        self.preview_btn = QPushButton("👁 Preview")
        self.preview_btn.clicked.connect(self.request_preview)

        self.generate_btn = QPushButton("🎨 Generate")
        self.generate_btn.clicked.connect(self.request_generation)
        self.generate_btn.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; background-color: #e8f4f8; color: black; }")

        buttons_layout.addWidget(self.preview_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.generate_btn)

        layout.addLayout(buttons_layout)

    def create_basic_parameters_group(self):
        """Create basic visualization parameters group."""
        group = QGroupBox("Basic Parameters")
        layout = QGridLayout(group)

        # Map type with delta options
        layout.addWidget(QLabel("Map Type:"), 0, 0)
        self.map_type_combo = QComboBox()

        # Base map types
        base_types = ["strain", "d-spacing", "peak_area", "peak_width", "gamma_y", "gamma_z", "background"]
        map_types = []

        # Add base types and their variants
        for base_type in base_types:
            map_types.append(base_type)
            map_types.append(f"delta {base_type}")
            map_types.append(f"abs {base_type}")
            map_types.append(f"diff {base_type}")

        self.map_type_combo.addItems(map_types)
        self.map_type_combo.currentTextChanged.connect(self.on_parameter_changed)
        layout.addWidget(self.map_type_combo, 0, 1)

        # Visualization mode
        layout.addWidget(QLabel("Mode:"), 1, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Standard", "Robust", "Robust L.L.", "Standard L.L."])
        self.mode_combo.currentTextChanged.connect(self.on_parameter_changed)
        layout.addWidget(self.mode_combo, 1, 1)

        # Color map
        layout.addWidget(QLabel("Color Map:"), 2, 0)
        self.color_combo = QComboBox()
        self.color_combo.addItems(["icefire", "viridis", "plasma", "inferno", "coolwarm", "RdBu_r"])
        self.color_combo.currentTextChanged.connect(self.on_parameter_changed)
        layout.addWidget(self.color_combo, 2, 1)

        return group

    def create_peak_parameters_group(self):
        """Create peak-specific parameters group."""
        group = QGroupBox("Peak-Specific Parameters")
        layout = QVBoxLayout(group)

        if not self.dataset:
            layout.addWidget(QLabel("No dataset loaded"))
            return group

        # Get available peaks from PeakConfig
        active_peaks = PeakConfig.get_active_peaks()

        for i, peak_position in enumerate(active_peaks):
            peak_metadata = PeakConfig.get_peak_metadata(peak_position)
            peak_frame = self.create_peak_control_frame(peak_position, peak_metadata, i)
            layout.addWidget(peak_frame)

        return group

    def create_peak_control_frame(self, peak_position, metadata, index):
        """Create control frame for individual peak."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        layout = QGridLayout(frame)

        # Peak header with name and position
        header_label = QLabel(f"{metadata['name']} ({peak_position:.2f}°)")
        header_label.setStyleSheet("font-weight: bold; color: black;")
        layout.addWidget(header_label, 0, 0, 1, 4)

        # Enabled checkbox
        enabled_check = QCheckBox("Enabled")
        enabled_check.setChecked(True)
        enabled_check.stateChanged.connect(self.on_parameter_changed)
        layout.addWidget(enabled_check, 1, 0)

        # Custom name entry
        name_label = QLabel("Display Name:")
        name_entry = QLineEdit(metadata['name'])
        name_entry.textChanged.connect(self.on_parameter_changed)
        layout.addWidget(name_label, 1, 1)
        layout.addWidget(name_entry, 1, 2, 1, 2)

        # Locked limits
        layout.addWidget(QLabel("Lower Limit:"), 2, 0)
        lower_limit = QDoubleSpinBox()
        lower_limit.setRange(-999.0, 999.0)
        lower_limit.setDecimals(3)
        lower_limit.setValue(metadata['typical_range'][0])
        lower_limit.valueChanged.connect(self.on_parameter_changed)
        layout.addWidget(lower_limit, 2, 1)

        layout.addWidget(QLabel("Upper Limit:"), 2, 2)
        upper_limit = QDoubleSpinBox()
        upper_limit.setRange(-999.0, 999.0)
        upper_limit.setDecimals(3)
        upper_limit.setValue(metadata['typical_range'][1])
        upper_limit.valueChanged.connect(self.on_parameter_changed)
        layout.addWidget(upper_limit, 2, 3)

        # Store controls for access
        self.peak_controls[peak_position] = {
            'enabled': enabled_check,
            'name': name_entry,
            'lower_limit': lower_limit,
            'upper_limit': upper_limit,
            'metadata': metadata,
            'index': index
        }

        return frame

    def create_advanced_options_group(self):
        """Create advanced options group."""
        group = QGroupBox("Advanced Options")
        layout = QGridLayout(group)

        # Save options
        self.save_csv_check = QCheckBox("Save CSV data")
        layout.addWidget(self.save_csv_check, 0, 0)

        self.plot_cof_check = QCheckBox("Plot with COF data")
        layout.addWidget(self.plot_cof_check, 0, 1)

        # Real-time preview
        self.realtime_check = QCheckBox("Real-time preview")
        self.realtime_check.setChecked(True)
        self.realtime_check.stateChanged.connect(self.toggle_realtime_preview)
        layout.addWidget(self.realtime_check, 1, 0)

        return group

    def on_parameter_changed(self):
        """Handle parameter changes for real-time preview."""
        if self.realtime_check.isChecked():
            # Restart timer for throttled preview
            self.preview_timer.start(500)  # 500ms delay

    def toggle_realtime_preview(self, state):
        """Toggle real-time preview on/off."""
        if state == Qt.Checked:
            self.request_preview()

    def request_preview(self):
        """Request preview generation."""
        params = self.collect_parameters()
        self.previewRequested.emit(params, self.name_entry.text())

    def request_generation(self):
        """Request full generation."""
        params = self.collect_parameters()
        self.generateRequested.emit(params, self.name_entry.text())

    def collect_parameters(self):
        """Collect all parameters from the tab."""
        params = {
            "Map_Type": self.map_type_combo.currentText(),
            "Mode": self.mode_combo.currentText(),
            "Color": self.color_combo.currentText(),
            "save_csv": self.save_csv_check.isChecked(),
            "plot_with_cof": self.plot_cof_check.isChecked(),
            "peaks": {}
        }

        # Collect peak-specific parameters
        for peak_pos, controls in self.peak_controls.items():
            if controls['enabled'].isChecked():
                params["peaks"][peak_pos] = {
                    "name": controls['name'].text(),
                    "lower_limit": controls['lower_limit'].value(),
                    "upper_limit": controls['upper_limit'].value(),
                    "metadata": controls['metadata'],
                    "index": controls['index']
                }

        return params


class AdvancedVisualizationWindow(QMainWindow):
    """Main window for advanced XRD data visualization."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced XRD Data Visualization Interface")
        self.setGeometry(100, 100, 1400, 900)

        # State variables
        self.current_dataset = None
        self.save_folder = ""
        self.generation_queue = []
        self.unique_counter = 0

        self.init_ui()
        self.refresh_zarr_files()

    def init_ui(self):
        """Initialize the main UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main horizontal splitter
        main_splitter = QSplitter(Qt.Horizontal)
        central_widget_layout = QVBoxLayout(central_widget)
        central_widget_layout.addWidget(main_splitter)

        # Left panel - dataset selection and controls
        left_panel = self.create_control_panel()
        main_splitter.addWidget(left_panel)

        # Right panel - image gallery
        self.image_gallery = ImageGalleryWidget()
        self.image_gallery.imageClicked.connect(self.on_image_clicked)
        main_splitter.addWidget(self.image_gallery)

        # Set splitter proportions (60% controls, 40% gallery)
        main_splitter.setSizes([840, 560])

        # Status bar
        self.statusBar().showMessage("Ready")

    def create_control_panel(self):
        """Create the left control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Dataset selection
        dataset_group = QGroupBox("Dataset Selection")
        dataset_layout = QVBoxLayout(dataset_group)

        # Refresh and load controls
        refresh_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_zarr_files)

        self.save_folder_btn = QPushButton("📁 Set Save Folder")
        self.save_folder_btn.clicked.connect(self.select_save_folder)

        refresh_layout.addWidget(refresh_btn)
        refresh_layout.addWidget(self.save_folder_btn)
        dataset_layout.addLayout(refresh_layout)

        # Dataset list
        self.dataset_list = QListWidget()
        self.dataset_list.itemClicked.connect(self.on_dataset_selected)
        dataset_layout.addWidget(self.dataset_list)

        # Dataset info
        self.dataset_info = QTextEdit()
        self.dataset_info.setReadOnly(True)
        self.dataset_info.setMaximumHeight(120)
        dataset_layout.addWidget(self.dataset_info)

        layout.addWidget(dataset_group)

        # Analysis tabs
        analysis_group = QGroupBox("Analysis Configurations")
        analysis_layout = QVBoxLayout(analysis_group)

        # Tab controls
        tab_controls_layout = QHBoxLayout()
        add_tab_btn = QPushButton("➕ Add Analysis")
        add_tab_btn.clicked.connect(self.add_analysis_tab)

        remove_tab_btn = QPushButton("➖ Remove Current")
        remove_tab_btn.clicked.connect(self.remove_current_tab)

        tab_controls_layout.addWidget(add_tab_btn)
        tab_controls_layout.addWidget(remove_tab_btn)
        tab_controls_layout.addStretch()
        analysis_layout.addLayout(tab_controls_layout)

        # Tab widget for analysis configurations
        self.analysis_tabs = QTabWidget()
        self.analysis_tabs.setTabsClosable(True)
        self.analysis_tabs.tabCloseRequested.connect(self.close_tab)
        analysis_layout.addWidget(self.analysis_tabs)

        layout.addWidget(analysis_group)

        # Global controls
        global_group = QGroupBox("Global Controls")
        global_layout = QVBoxLayout(global_group)

        # Batch generation
        batch_btn = QPushButton("🚀 Generate All Tabs")
        batch_btn.clicked.connect(self.generate_all_tabs)
        batch_btn.setStyleSheet("QPushButton { font-weight: bold; padding: 10px; background-color: #d4eaff; color: black; border: 1px solid #999; }")

        global_layout.addWidget(batch_btn)
        layout.addWidget(global_group)

        # Add initial analysis tab
        self.add_analysis_tab()

        return panel

    def refresh_zarr_files(self):
        """Refresh the list of available Zarr datasets."""
        self.dataset_list.clear()

        # Try multiple possible Zarr directory locations
        possible_zarr_paths = [
            "Zarr",  # Relative to current working directory
            os.path.join("..", "Zarr"),  # One level up
            os.path.join("XRD", "Zarr"),  # In XRD subdirectory
            os.path.abspath("Zarr"),  # Absolute path
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Zarr"),  # Relative to script
        ]

        zarr_base = None
        for path in possible_zarr_paths:
            if os.path.exists(path):
                zarr_base = path
                break

        if not zarr_base:
            self.statusBar().showMessage("No Zarr directory found. Generate data first.")
            self.dataset_info.setText("No Zarr directory found.\n\nTo create datasets:\n1. Use interface.py to generate data\n2. Or use batch_processor.py for multiple datasets\n3. Then refresh this list")
            return

        print(f"Using Zarr directory: {os.path.abspath(zarr_base)}")

        # Find Zarr directories
        zarr_dirs = []
        try:
            for item in os.listdir(zarr_base):
                item_path = os.path.join(zarr_base, item)
                if os.path.isdir(item_path) and item != "Old_Zarr":
                    # Check if it looks like a Zarr dataset (contains .zarray or .zgroup files)
                    if any(f.endswith(('.zarray', '.zgroup', '.zattrs')) for f in os.listdir(item_path)):
                        zarr_dirs.append(item)
        except Exception as e:
            self.statusBar().showMessage(f"Error scanning Zarr directory: {e}")
            return

        if not zarr_dirs:
            self.statusBar().showMessage("No Zarr datasets found in directory")
            self.dataset_info.setText(f"Zarr directory found: {zarr_base}\n\nBut no datasets present.\n\nGenerate data first using:\n- interface.py (single dataset)\n- batch_processor.py (multiple datasets)")
            return

        # Sort by modification time
        try:
            zarr_dirs.sort(key=lambda x: os.path.getmtime(os.path.join(zarr_base, x)), reverse=True)
        except Exception:
            zarr_dirs.sort()  # Fallback to alphabetical

        # Add to list
        for zarr_dir in zarr_dirs:
            item = QListWidgetItem(zarr_dir)
            zarr_path = os.path.join(zarr_base, zarr_dir)
            try:
                mod_time = datetime.fromtimestamp(os.path.getmtime(zarr_path))
                item.setToolTip(f"Path: {zarr_path}\nModified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception:
                item.setToolTip(f"Path: {zarr_path}")
            self.dataset_list.addItem(item)

        self.statusBar().showMessage(f"Found {len(zarr_dirs)} datasets in {zarr_base}")
        self.dataset_info.setText(f"Zarr directory: {zarr_base}\nDatasets found: {len(zarr_dirs)}\n\nSelect a dataset to load.")

    def on_dataset_selected(self, item):
        """Handle dataset selection."""
        zarr_name = item.text()

        # Find the correct Zarr base path (same logic as refresh)
        possible_zarr_paths = [
            "Zarr",
            os.path.join("..", "Zarr"),
            os.path.join("XRD", "Zarr"),
            os.path.abspath("Zarr"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Zarr"),
        ]

        zarr_base = None
        for path in possible_zarr_paths:
            if os.path.exists(path):
                zarr_base = path
                break

        if not zarr_base:
            QMessageBox.critical(self, "Dataset Error", "Zarr directory not found")
            return

        zarr_path = os.path.join(zarr_base, zarr_name)

        try:
            # Load dataset
            self.current_dataset = XRDDataset.load(zarr_path)

            # Update info display
            info = f"Dataset: {zarr_name}\n"
            info += f"Sample: {self.current_dataset.params.sample}\n"
            info += f"Setting: {self.current_dataset.params.setting}\n"
            info += f"Stage: {self.current_dataset.params.stage.name}\n"
            info += f"Shape: {self.current_dataset.data.shape}\n"
            info += f"Measurements: {list(self.current_dataset.col_idx.keys())}"

            self.dataset_info.setText(info)

            # Update all analysis tabs with new dataset
            for i in range(self.analysis_tabs.count()):
                tab_widget = self.analysis_tabs.widget(i)
                if isinstance(tab_widget, AnalysisTabWidget):
                    tab_widget.dataset = self.current_dataset

            self.statusBar().showMessage(f"Loaded: {zarr_name}")

        except Exception as e:
            QMessageBox.critical(self, "Dataset Error", f"Failed to load dataset: {e}")
            self.dataset_info.setText(f"Error loading: {e}")

    def select_save_folder(self):
        """Select folder for saving visualizations."""
        folder = QFileDialog.getExistingDirectory(self, "Select Save Folder")
        if folder:
            self.save_folder = folder
            self.save_folder_btn.setText(f"{os.path.basename(folder)}")
            self.statusBar().showMessage(f"Save folder: {folder}")

    def add_analysis_tab(self):
        """Add a new analysis tab."""
        tab_count = self.analysis_tabs.count() + 1
        tab_name = f"Analysis {tab_count}"

        analysis_tab = AnalysisTabWidget(tab_name, self.current_dataset)
        analysis_tab.generateRequested.connect(self.generate_visualization)
        analysis_tab.previewRequested.connect(self.preview_visualization)

        index = self.analysis_tabs.addTab(analysis_tab, tab_name)
        self.analysis_tabs.setCurrentIndex(index)

    def remove_current_tab(self):
        """Remove the currently active tab."""
        current_index = self.analysis_tabs.currentIndex()
        if current_index >= 0 and self.analysis_tabs.count() > 1:
            self.analysis_tabs.removeTab(current_index)

    def close_tab(self, index):
        """Close a specific tab."""
        if self.analysis_tabs.count() > 1:
            self.analysis_tabs.removeTab(index)

    def generate_unique_filename(self, base_params, analysis_name):
        """Generate unique timestamp-based filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.unique_counter += 1

        # Clean analysis name for filename
        clean_name = "".join(c for c in analysis_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_name = clean_name.replace(' ', '_')

        # Create filename
        filename = f"{timestamp}_{clean_name}_{base_params['Map_Type'].replace(' ', '_')}_{self.unique_counter:03d}"
        return filename

    def preview_visualization(self, params, analysis_name):
        """Generate preview visualization."""
        if not self.current_dataset:
            self.statusBar().showMessage("No dataset selected")
            return

        self.statusBar().showMessage(f"Generating preview for {analysis_name}...")
        # Note: Preview implementation would be lighter weight
        # For now, just show status

    def generate_visualization(self, params, analysis_name):
        """Generate full visualization."""
        if not self.current_dataset:
            QMessageBox.warning(self, "No Dataset", "Please select a dataset first.")
            return

        if not self.save_folder:
            QMessageBox.warning(self, "No Save Folder", "Please select a save folder first.")
            return

        try:
            self.statusBar().showMessage(f"Generating visualization for {analysis_name}...")
            QApplication.processEvents()

            # Generate unique filename
            filename_base = self.generate_unique_filename(params, analysis_name)

            # Create visualization parameters
            vis_values = {
                "Map_Type": params["Map_Type"],
                "Mode": params["Mode"],
                "Color": params["Color"],
                "save_plot_folder": self.save_folder,
                "save_csv": params["save_csv"],
                "plot_with_cof": params["plot_with_cof"],
                "sample": self.current_dataset.params.sample,
                "Az Start": "-90",
                "Az End": "90",
                "spacing": "5"
            }

            # Generate visualizations for enabled peaks
            for peak_pos, peak_info in params["peaks"].items():
                if peak_pos in params["peaks"]:  # Enabled peaks only
                    # Use the existing visualization system
                    from data_visualization import GraphParams, GraphSetting, Location

                    # Convert mode to enum
                    mode_mapping = {
                        "Robust L.L.": "ROBUST_LL",
                        "Standard L.L.": "STANDARD_LL"
                    }
                    graph_input = mode_mapping.get(params["Mode"], params["Mode"].upper())
                    graph_type = GraphSetting[graph_input]

                    # Set locked limits from peak parameters
                    locked_limits = (peak_info["lower_limit"], peak_info["upper_limit"])
                    vis_values["Locked Limits"] = locked_limits

                    graph_params = GraphParams(
                        graph_type=graph_type,
                        locked_lims=locked_limits,
                        peak_index=peak_info["index"],
                        peak_miller=int(peak_info["metadata"]["miller"]) if peak_info["metadata"]["miller"].isdigit() else 200,
                        label=params["Map_Type"],
                        sample=self.current_dataset.params.sample,
                        stage=self.current_dataset.params.stage,
                        in_situ=(self.current_dataset.params.stage == Stages.CONT),
                        loc=Location.FULL,
                        ranges=(-90, 90)
                    )

                    # Generate visualization
                    data_visualization.create_visualization(self.current_dataset, graph_params, vis_values)

                    # Find the generated image and add to gallery
                    # This is a simplified approach - in practice, you'd want more robust file tracking
                    expected_path = os.path.join(
                        self.save_folder,
                        self.current_dataset.params.sample,
                        f"{self.current_dataset.params.sample}-{self.current_dataset.params.stage.name}-{graph_params.peak_miller}-{params['Map_Type'].replace(' ', '')}.png"
                    )

                    if os.path.exists(expected_path):
                        # Add to image gallery
                        image_metadata = {
                            "peak_name": peak_info["name"],
                            "map_type": params["Map_Type"],
                            "analysis_name": analysis_name,
                            "peak_position": peak_pos,
                            "filename_base": filename_base
                        }
                        self.image_gallery.add_image(expected_path, image_metadata)

            self.statusBar().showMessage(f"Generated visualization for {analysis_name}")

        except Exception as e:
            error_msg = f"Error generating visualization: {e}"
            self.statusBar().showMessage(f"{error_msg}")
            QMessageBox.critical(self, "Generation Error", error_msg)

    def generate_all_tabs(self):
        """Generate visualizations for all tabs."""
        if not self.current_dataset:
            QMessageBox.warning(self, "No Dataset", "Please select a dataset first.")
            return

        if not self.save_folder:
            QMessageBox.warning(self, "No Save Folder", "Please select a save folder first.")
            return

        # Collect all tab parameters
        all_params = []
        for i in range(self.analysis_tabs.count()):
            tab_widget = self.analysis_tabs.widget(i)
            if isinstance(tab_widget, AnalysisTabWidget):
                params = tab_widget.collect_parameters()
                analysis_name = tab_widget.name_entry.text()
                all_params.append((params, analysis_name))

        if not all_params:
            QMessageBox.information(self, "No Analyses", "No analysis tabs found.")
            return

        # Generate all visualizations
        self.statusBar().showMessage(f"Generating {len(all_params)} visualizations...")

        for i, (params, analysis_name) in enumerate(all_params):
            self.statusBar().showMessage(f"Generating {i+1}/{len(all_params)}: {analysis_name}")
            QApplication.processEvents()
            self.generate_visualization(params, analysis_name)

        self.statusBar().showMessage(f"Completed all {len(all_params)} visualizations")

    def on_image_clicked(self, image_path):
        """Handle image click in gallery."""
        # For now, just show info - could implement zoom, edit, etc.
        QMessageBox.information(self, "Image Info", f"Clicked: {os.path.basename(image_path)}")


def main():
    """Main entry point for the advanced visualization interface."""
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle('Fusion')

    # Light palette - black text on white background
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(255, 255, 255))  # White background
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))   # Black text
    palette.setColor(QPalette.Base, QColor(255, 255, 255))   # White input backgrounds
    palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))  # Light gray alternate
    palette.setColor(QPalette.Text, QColor(0, 0, 0))         # Black text in inputs
    palette.setColor(QPalette.Button, QColor(240, 240, 240)) # Light gray buttons
    palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))   # Black button text
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0)) # Red bright text
    palette.setColor(QPalette.Link, QColor(42, 130, 218))    # Blue links
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))  # Blue selection
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))  # White selected text
    app.setPalette(palette)

    window = AdvancedVisualizationWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()