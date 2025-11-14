#!/usr/bin/env python3
"""
XRD Recipe Builder
==================
Simple GUI for creating JSON recipe files for XRD data processing.
Stays open to allow creation of multiple recipes for batch processing.

This replaces the old interface.py with a cleaner, focused approach.
Recipes are saved to the recipes/ directory for batch processing.

Author(s): William Gonzalez, Adrian Guzman
Date: October 2025
Version: Beta 0.1
"""

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QWidget, QFileDialog, QLineEdit, QComboBox, QMessageBox, QGridLayout,
    QSpinBox, QDoubleSpinBox, QTextEdit, QGroupBox, QListWidget, QListWidgetItem,
    QFormLayout, QScrollArea, QCheckBox
)
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt
import json
import os
import sys
from datetime import datetime
import glob


class PeakWidget(QWidget):
    """Widget for managing a single peak configuration."""

    def __init__(self, peak_data=None):
        super().__init__()
        self.setup_ui()
        if peak_data:
            self.load_peak_data(peak_data)

    def setup_ui(self):
        layout = QHBoxLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Peak Name (e.g., Martensite 211)")

        self.miller_edit = QLineEdit()
        self.miller_edit.setPlaceholderText("Miller Index (e.g., 211)")

        self.position_spin = QDoubleSpinBox()
        self.position_spin.setRange(0.1, 20.0)
        self.position_spin.setDecimals(3)
        self.position_spin.setSingleStep(0.001)

        self.min_limit_spin = QDoubleSpinBox()
        self.min_limit_spin.setRange(0.1, 20.0)
        self.min_limit_spin.setDecimals(3)
        self.min_limit_spin.setSingleStep(0.001)

        self.max_limit_spin = QDoubleSpinBox()
        self.max_limit_spin.setRange(0.1, 20.0)
        self.max_limit_spin.setDecimals(3)
        self.max_limit_spin.setSingleStep(0.001)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setMaximumWidth(80)

        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("Miller:"))
        layout.addWidget(self.miller_edit)
        layout.addWidget(QLabel("Position:"))
        layout.addWidget(self.position_spin)
        layout.addWidget(QLabel("Min:"))
        layout.addWidget(self.min_limit_spin)
        layout.addWidget(QLabel("Max:"))
        layout.addWidget(self.max_limit_spin)
        layout.addWidget(self.remove_btn)

        self.setLayout(layout)

    def load_peak_data(self, data):
        self.name_edit.setText(data.get("name", ""))
        self.miller_edit.setText(data.get("miller_index", ""))
        self.position_spin.setValue(data.get("position", 8.0))
        limits = data.get("limits", [7.5, 8.5])
        self.min_limit_spin.setValue(limits[0])
        self.max_limit_spin.setValue(limits[1])

    def get_peak_data(self):
        return {
            "name": self.name_edit.text(),
            "miller_index": self.miller_edit.text(),
            "position": self.position_spin.value(),
            "limits": [self.min_limit_spin.value(), self.max_limit_spin.value()]
        }


class RecipeBuilder(QMainWindow):
    def __init__(self, workspace_path=None):
        super().__init__()
        self.setWindowTitle("XRD Recipe Builder v3.0")
        self.setGeometry(100, 100, 900, 700)

        # Store workspace path
        self.workspace_path = workspace_path

        # Default values
        self.default_values = {
            "home_dir": workspace_path if workspace_path else os.getcwd(),  # Use workspace if provided
            "images_path": "",  # User must specify
            "refs_path": "",    # Optional
            "sample": "A1",
            "setting": "Standard",
            "stage": "CONT",
            "step": 1,
            "spacing": 5,
            "frame_start": 0,
            "frame_end": -1,
            "az_start": -110,
            "az_end": 110,
            "exposure": "019",
            "notes": ""
        }

        self.exposure_defaults = {
            "Standard": "1", "Speed": "009", "SpeedTall": "019",
            "Profile": "1", "Oxide": "019", "FineGrid": "1",
            "30x50": "1", "1x50": "1"
        }

        self.peak_widgets = []
        self.setup_ui()
        self.load_defaults()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout()

        # Scroll area for the form
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()

        # Home Directory Group (for outputs)
        home_group = QGroupBox("Output Directory")
        home_layout = QVBoxLayout()

        home_dir_layout = QHBoxLayout()
        self.home_dir_edit = QLineEdit()
        self.home_dir_edit.setPlaceholderText("Select root directory for processed data and analysis")
        self.home_dir_btn = QPushButton("Browse")
        self.home_dir_btn.clicked.connect(lambda: self.browse_folder(self.home_dir_edit))
        home_dir_layout.addWidget(QLabel("Home Directory:"))
        home_dir_layout.addWidget(self.home_dir_edit)
        home_dir_layout.addWidget(self.home_dir_btn)

        home_layout.addLayout(home_dir_layout)
        home_layout.addWidget(QLabel("Note: Processed data will be saved to {home}/Processed/, analysis to {home}/Analysis/"))

        home_group.setLayout(home_layout)

        # Data Locations Group (NEW - explicit paths)
        data_group = QGroupBox("Input Data Locations")
        data_layout = QVBoxLayout()

        # Images path
        images_layout = QHBoxLayout()
        self.images_path_edit = QLineEdit()
        self.images_path_edit.setPlaceholderText("Select directory containing diffraction images")
        self.images_path_btn = QPushButton("Browse")
        self.images_path_btn.clicked.connect(lambda: self.browse_folder(self.images_path_edit))
        images_layout.addWidget(QLabel("Images Directory:"))
        images_layout.addWidget(self.images_path_edit)
        images_layout.addWidget(self.images_path_btn)

        # Refs path (optional)
        refs_layout = QHBoxLayout()
        self.refs_path_edit = QLineEdit()
        self.refs_path_edit.setPlaceholderText("Optional: Select directory containing reference images")
        self.refs_path_btn = QPushButton("Browse")
        self.refs_path_btn.clicked.connect(lambda: self.browse_folder(self.refs_path_edit))
        self.refs_path_clear_btn = QPushButton("Clear")
        self.refs_path_clear_btn.clicked.connect(lambda: self.refs_path_edit.clear())
        self.refs_path_clear_btn.setMaximumWidth(60)
        refs_layout.addWidget(QLabel("References Directory:"))
        refs_layout.addWidget(self.refs_path_edit)
        refs_layout.addWidget(self.refs_path_btn)
        refs_layout.addWidget(self.refs_path_clear_btn)

        self.no_refs_checkbox = QCheckBox("No reference images (strain calculation will be disabled)")
        self.no_refs_checkbox.stateChanged.connect(self.toggle_refs_input)

        data_layout.addLayout(images_layout)
        data_layout.addLayout(refs_layout)
        data_layout.addWidget(self.no_refs_checkbox)
        data_layout.addWidget(QLabel("Note: If no references provided, strain analysis will be skipped"))

        data_group.setLayout(data_layout)

        # Basic Parameters Group
        basic_group = QGroupBox("Basic Parameters")
        basic_layout = QFormLayout()

        self.sample_edit = QLineEdit()
        self.setting_combo = QComboBox()
        self.setting_combo.addItems(["Standard", "Speed", "SpeedTall", "Profile", "Oxide", "FineGrid", "30x50", "1x50"])
        self.setting_combo.currentTextChanged.connect(self.update_exposure)

        self.stage_edit = QLineEdit()
        self.exposure_edit = QLineEdit()

        basic_layout.addRow("Sample:", self.sample_edit)
        basic_layout.addRow("Setting:", self.setting_combo)
        basic_layout.addRow("Stage:", self.stage_edit)
        basic_layout.addRow("Exposure:", self.exposure_edit)

        basic_group.setLayout(basic_layout)

        # Calibration Files Group
        files_group = QGroupBox("Calibration Files")
        files_layout = QFormLayout()

        self.control_file_edit = QLineEdit()
        self.control_file_btn = QPushButton("Browse")
        self.control_file_btn.clicked.connect(lambda: self.browse_file(self.control_file_edit, "Control Files (*.imctrl)"))

        self.mask_file_edit = QLineEdit()
        self.mask_file_btn = QPushButton("Browse")
        self.mask_file_btn.clicked.connect(lambda: self.browse_file(self.mask_file_edit, "Mask Files (*.immask)"))

        control_layout = QHBoxLayout()
        control_layout.addWidget(self.control_file_edit)
        control_layout.addWidget(self.control_file_btn)

        mask_layout = QHBoxLayout()
        mask_layout.addWidget(self.mask_file_edit)
        mask_layout.addWidget(self.mask_file_btn)

        files_layout.addRow("Control File:", control_layout)
        files_layout.addRow("Mask File:", mask_layout)

        files_group.setLayout(files_layout)

        # Detector & Beam Parameters Group (NEW)
        detector_group = QGroupBox("Detector & Beam Parameters")
        detector_layout = QFormLayout()

        self.pixel_x_spin = QDoubleSpinBox()
        self.pixel_x_spin.setRange(1.0, 500.0)
        self.pixel_x_spin.setDecimals(1)
        self.pixel_x_spin.setValue(172.0)
        self.pixel_x_spin.setSuffix(" μm")

        self.pixel_y_spin = QDoubleSpinBox()
        self.pixel_y_spin.setRange(1.0, 500.0)
        self.pixel_y_spin.setDecimals(1)
        self.pixel_y_spin.setValue(172.0)
        self.pixel_y_spin.setSuffix(" μm")

        self.wavelength_spin = QDoubleSpinBox()
        self.wavelength_spin.setRange(0.05, 5.0)
        self.wavelength_spin.setDecimals(4)
        self.wavelength_spin.setValue(0.2400)
        self.wavelength_spin.setSuffix(" Å")

        self.detector_x_spin = QSpinBox()
        self.detector_x_spin.setRange(100, 5000)
        self.detector_x_spin.setValue(1475)
        self.detector_x_spin.setSuffix(" px")

        self.detector_y_spin = QSpinBox()
        self.detector_y_spin.setRange(100, 5000)
        self.detector_y_spin.setValue(1679)
        self.detector_y_spin.setSuffix(" px")

        # Detector preset button
        detector_preset_layout = QHBoxLayout()
        pilatus300k_btn = QPushButton("Pilatus 300K")
        pilatus300k_btn.clicked.connect(lambda: self.set_detector_preset("Pilatus 300K"))
        pilatus1m_btn = QPushButton("Pilatus 1M")
        pilatus1m_btn.clicked.connect(lambda: self.set_detector_preset("Pilatus 1M"))
        pilatus2m_btn = QPushButton("Pilatus 2M")
        pilatus2m_btn.clicked.connect(lambda: self.set_detector_preset("Pilatus 2M"))
        detector_preset_layout.addWidget(pilatus300k_btn)
        detector_preset_layout.addWidget(pilatus1m_btn)
        detector_preset_layout.addWidget(pilatus2m_btn)
        detector_preset_layout.addStretch()

        detector_layout.addRow("Pixel Size X:", self.pixel_x_spin)
        detector_layout.addRow("Pixel Size Y:", self.pixel_y_spin)
        detector_layout.addRow("Wavelength:", self.wavelength_spin)
        detector_layout.addRow("Detector Width:", self.detector_x_spin)
        detector_layout.addRow("Detector Height:", self.detector_y_spin)
        detector_layout.addRow("Presets:", detector_preset_layout)

        detector_group.setLayout(detector_layout)

        # Calibration Options Group (NEW)
        calibration_group = QGroupBox("Calibration Options")
        calibration_layout = QVBoxLayout()

        self.auto_calibrate_checkbox = QCheckBox("Auto-calibrate from ceria images")
        self.auto_calibrate_checkbox.stateChanged.connect(self.toggle_calibration_inputs)
        calibration_layout.addWidget(self.auto_calibrate_checkbox)

        # Ceria folder input (hidden by default)
        ceria_layout = QHBoxLayout()
        self.ceria_folder_edit = QLineEdit()
        self.ceria_folder_edit.setEnabled(False)
        self.ceria_folder_btn = QPushButton("Browse")
        self.ceria_folder_btn.setEnabled(False)
        self.ceria_folder_btn.clicked.connect(lambda: self.browse_folder(self.ceria_folder_edit))
        ceria_layout.addWidget(QLabel("Ceria Folder:"))
        ceria_layout.addWidget(self.ceria_folder_edit)
        ceria_layout.addWidget(self.ceria_folder_btn)
        calibration_layout.addLayout(ceria_layout)

        # Calibrant selection
        calibrant_layout = QHBoxLayout()
        self.calibrant_combo = QComboBox()
        self.calibrant_combo.addItems(["CeO2", "Si    SRM640c", "LaB6", "Al2O3"])
        self.calibrant_combo.setEnabled(False)
        calibrant_layout.addWidget(QLabel("Calibrant:"))
        calibrant_layout.addWidget(self.calibrant_combo)
        calibrant_layout.addStretch()
        calibration_layout.addLayout(calibrant_layout)

        # Initial beam center (for calibration)
        center_layout = QHBoxLayout()
        self.beam_center_x_spin = QDoubleSpinBox()
        self.beam_center_x_spin.setRange(0, 5000)
        self.beam_center_x_spin.setDecimals(1)
        self.beam_center_x_spin.setValue(737.5)
        self.beam_center_x_spin.setEnabled(False)
        self.beam_center_y_spin = QDoubleSpinBox()
        self.beam_center_y_spin.setRange(0, 5000)
        self.beam_center_y_spin.setDecimals(1)
        self.beam_center_y_spin.setValue(839.5)
        self.beam_center_y_spin.setEnabled(False)
        center_layout.addWidget(QLabel("Initial Beam Center:"))
        center_layout.addWidget(self.beam_center_x_spin)
        center_layout.addWidget(QLabel("×"))
        center_layout.addWidget(self.beam_center_y_spin)
        center_layout.addStretch()
        calibration_layout.addLayout(center_layout)

        calibration_group.setLayout(calibration_layout)

        # Processing Parameters Group
        processing_group = QGroupBox("Processing Parameters")
        processing_layout = QFormLayout()

        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 100)

        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(1, 50)

        self.frame_start_spin = QSpinBox()
        self.frame_start_spin.setRange(0, 999999)

        self.frame_end_spin = QSpinBox()
        self.frame_end_spin.setRange(-1, 999999)

        self.az_start_spin = QSpinBox()
        self.az_start_spin.setRange(-360, 360)

        self.az_end_spin = QSpinBox()
        self.az_end_spin.setRange(-360, 360)

        processing_layout.addRow("Step:", self.step_spin)
        processing_layout.addRow("Spacing:", self.spacing_spin)
        processing_layout.addRow("Frame Start:", self.frame_start_spin)
        processing_layout.addRow("Frame End:", self.frame_end_spin)
        processing_layout.addRow("Azimuth Start:", self.az_start_spin)
        processing_layout.addRow("Azimuth End:", self.az_end_spin)

        processing_group.setLayout(processing_layout)

        # Peaks Group
        peaks_group = QGroupBox("Peak Configuration")
        peaks_layout = QVBoxLayout()

        # Add peak button
        add_peak_btn = QPushButton("Add Peak")
        add_peak_btn.clicked.connect(self.add_peak)
        peaks_layout.addWidget(add_peak_btn)

        # Peaks container
        self.peaks_container = QWidget()
        self.peaks_layout = QVBoxLayout()
        self.peaks_container.setLayout(self.peaks_layout)
        peaks_layout.addWidget(self.peaks_container)

        peaks_group.setLayout(peaks_layout)

        # Notes Group
        notes_group = QGroupBox("Notes")
        notes_layout = QVBoxLayout()

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(100)
        notes_layout.addWidget(self.notes_edit)

        notes_group.setLayout(notes_layout)

        # Add all groups to scroll layout
        scroll_layout.addWidget(home_group)
        scroll_layout.addWidget(data_group)
        scroll_layout.addWidget(basic_group)
        scroll_layout.addWidget(files_group)
        scroll_layout.addWidget(detector_group)
        scroll_layout.addWidget(calibration_group)
        scroll_layout.addWidget(processing_group)
        scroll_layout.addWidget(peaks_group)
        scroll_layout.addWidget(notes_group)

        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)

        # Buttons
        button_layout = QHBoxLayout()

        save_btn = QPushButton("Save Recipe")
        save_btn.clicked.connect(self.save_recipe)

        load_btn = QPushButton("Load Recipe")
        load_btn.clicked.connect(self.load_recipe)

        clear_btn = QPushButton("Clear Form")
        clear_btn.clicked.connect(self.clear_form)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(load_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()

        # Add to main layout
        main_layout.addWidget(scroll)
        main_layout.addLayout(button_layout)

        central_widget.setLayout(main_layout)

    def toggle_refs_input(self, state):
        """Enable/disable refs input based on checkbox."""
        disabled = (state == 2)  # Qt.Checked == 2
        self.refs_path_edit.setDisabled(disabled)
        self.refs_path_btn.setDisabled(disabled)
        self.refs_path_clear_btn.setDisabled(disabled)
        if disabled:
            self.refs_path_edit.clear()

    def load_defaults(self):
        """Load default values into the form."""
        self.home_dir_edit.setText(self.default_values["home_dir"])
        self.images_path_edit.setText(self.default_values["images_path"])
        self.refs_path_edit.setText(self.default_values["refs_path"])
        self.sample_edit.setText(self.default_values["sample"])
        self.setting_combo.setCurrentText(self.default_values["setting"])
        self.stage_edit.setText(self.default_values["stage"])
        self.step_spin.setValue(self.default_values["step"])
        self.spacing_spin.setValue(self.default_values["spacing"])
        self.frame_start_spin.setValue(self.default_values["frame_start"])
        self.frame_end_spin.setValue(self.default_values["frame_end"])
        self.az_start_spin.setValue(self.default_values["az_start"])
        self.az_end_spin.setValue(self.default_values["az_end"])
        self.exposure_edit.setText(self.default_values["exposure"])
        self.notes_edit.setPlainText(self.default_values["notes"])

        # Add default peak
        self.add_peak({
            "name": "Martensite 211",
            "miller_index": "211",
            "position": 8.46,
            "limits": [8.2, 8.8]
        })

    def update_exposure(self, setting):
        """Update exposure based on setting selection."""
        exposure = self.exposure_defaults.get(setting, "019")
        self.exposure_edit.setText(exposure)

    def set_detector_preset(self, preset):
        """Set detector parameters based on preset selection."""
        presets = {
            "Pilatus 300K": {
                "pixel_size": (172.0, 172.0),
                "detector_size": (1475, 1679)
            },
            "Pilatus 1M": {
                "pixel_size": (172.0, 172.0),
                "detector_size": (1043, 981)
            },
            "Pilatus 2M": {
                "pixel_size": (172.0, 172.0),
                "detector_size": (1679, 1475)
            }
        }

        if preset in presets:
            config = presets[preset]
            self.pixel_x_spin.setValue(config["pixel_size"][0])
            self.pixel_y_spin.setValue(config["pixel_size"][1])
            self.detector_x_spin.setValue(config["detector_size"][0])
            self.detector_y_spin.setValue(config["detector_size"][1])
            # Update default beam center to detector center
            self.beam_center_x_spin.setValue(config["detector_size"][0] / 2.0)
            self.beam_center_y_spin.setValue(config["detector_size"][1] / 2.0)

    def toggle_calibration_inputs(self, state):
        """Enable/disable calibration inputs based on checkbox state."""
        enabled = (state == 2)  # Qt.Checked == 2
        self.ceria_folder_edit.setEnabled(enabled)
        self.ceria_folder_btn.setEnabled(enabled)
        self.calibrant_combo.setEnabled(enabled)
        self.beam_center_x_spin.setEnabled(enabled)
        self.beam_center_y_spin.setEnabled(enabled)
        # Disable manual control file when auto-calibrate is enabled
        self.control_file_edit.setEnabled(not enabled)
        self.control_file_btn.setEnabled(not enabled)

    def browse_folder(self, line_edit):
        """Browse for folder and update line edit."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            line_edit.setText(folder.replace('\\', '/'))

    def browse_file(self, line_edit, file_filter):
        """Browse for file and update line edit."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", file_filter)
        if file_path:
            line_edit.setText(file_path.replace('\\', '/'))

    def add_peak(self, peak_data=None):
        """Add a new peak widget."""
        peak_widget = PeakWidget(peak_data)
        peak_widget.remove_btn.clicked.connect(lambda: self.remove_peak(peak_widget))

        self.peak_widgets.append(peak_widget)
        self.peaks_layout.addWidget(peak_widget)

    def remove_peak(self, peak_widget):
        """Remove a peak widget."""
        if len(self.peak_widgets) <= 1:
            QMessageBox.warning(self, "Warning", "At least one peak must be configured.")
            return

        self.peak_widgets.remove(peak_widget)
        self.peaks_layout.removeWidget(peak_widget)
        peak_widget.deleteLater()

    def collect_form_data(self):
        """Collect all form data into a dictionary."""
        # Collect peaks data
        peaks_data = []
        for widget in self.peak_widgets:
            peak_data = widget.get_peak_data()
            if peak_data["name"] and peak_data["miller_index"]:
                peaks_data.append(peak_data)

        if not peaks_data:
            raise ValueError("At least one valid peak must be configured.")

        # Get refs path (None if checkbox is checked or field is empty)
        refs_path = self.refs_path_edit.text().strip()
        if self.no_refs_checkbox.isChecked() or not refs_path:
            refs_path = None

        # Build recipe dictionary
        recipe = {
            "home_dir": self.home_dir_edit.text(),
            "images_path": self.images_path_edit.text(),
            "refs_path": refs_path,
            "sample": self.sample_edit.text(),
            "setting": self.setting_combo.currentText(),
            "stage": self.stage_edit.text(),
            "control_file": self.control_file_edit.text(),
            "mask_file": self.mask_file_edit.text(),
            "exposure": self.exposure_edit.text(),
            "step": self.step_spin.value(),
            "spacing": self.spacing_spin.value(),
            "frame_start": self.frame_start_spin.value(),
            "frame_end": self.frame_end_spin.value(),
            "az_start": self.az_start_spin.value(),
            "az_end": self.az_end_spin.value(),
            "active_peaks": peaks_data,
            "notes": self.notes_edit.toPlainText(),

            # Detector parameters (REQUIRED)
            "detector_params": {
                "pixel_size": [self.pixel_x_spin.value(), self.pixel_y_spin.value()],
                "wavelength": self.wavelength_spin.value(),
                "detector_size": [self.detector_x_spin.value(), self.detector_y_spin.value()]
            }
        }

        # Add calibration configuration if auto-calibrate is enabled
        if self.auto_calibrate_checkbox.isChecked():
            recipe["calibration"] = {
                "auto_calibrate": True,
                "ceria_folder": self.ceria_folder_edit.text(),
                "calibrant": self.calibrant_combo.currentText(),
                "initial_params": {
                    "center": [self.beam_center_x_spin.value(), self.beam_center_y_spin.value()],
                    "pixLimit": 2,
                    "cutoff": 5.0,
                    "DetDepth": 0.03,
                    "calibdmin": 0.5
                }
            }
        else:
            recipe["calibration"] = {
                "auto_calibrate": False
            }

        return recipe

    def save_recipe(self):
        """Save the current recipe to a JSON file."""
        try:
            data = self.collect_form_data()

            # Validate required fields
            required_fields = ["home_dir", "images_path", "sample", "setting", "stage", "control_file", "mask_file"]
            missing_fields = [field for field in required_fields if not data[field]]

            if missing_fields:
                QMessageBox.warning(self, "Missing Data",
                                  f"Please fill in: {', '.join(missing_fields)}")
                return

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            peak_names = "_".join([peak["miller_index"] for peak in data["active_peaks"]])
            filename = f"{data['sample']}_{data['setting']}_{data['stage']}_{peak_names}_{timestamp}.json"

            # Save to recipes directory within home_dir (use new path structure)
            from XRD.utils.path_manager import get_recipes_path, ensure_directory_exists

            recipe_dir = get_recipes_path(data["home_dir"])
            ensure_directory_exists(recipe_dir)

            recipe_path = os.path.join(recipe_dir, filename)

            with open(recipe_path, 'w') as f:
                json.dump(data, f, indent=4)

            QMessageBox.information(self, "Success", f"Recipe saved as:\n{filename}\n\nLocation:\n{recipe_path}")

        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save recipe:\n{str(e)}")

    def load_recipe(self):
        """Load a recipe from a JSON file."""
        # Default to recipes directory in current working directory
        default_dir = "recipes/"
        if hasattr(self, 'home_dir_edit') and self.home_dir_edit.text():
            from XRD.utils.path_manager import get_recipes_path
            default_dir = get_recipes_path(self.home_dir_edit.text())

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Recipe", default_dir, "JSON Files (*.json)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Clear existing peaks
            for widget in self.peak_widgets[:]:
                self.remove_peak_force(widget)

            # Load home directory and data paths
            self.home_dir_edit.setText(data.get("home_dir", os.getcwd()))
            self.images_path_edit.setText(data.get("images_path", ""))

            # Load refs path (handle None)
            refs_path = data.get("refs_path", "")
            if refs_path is None or refs_path == "":
                self.refs_path_edit.setText("")
                self.no_refs_checkbox.setChecked(True)
            else:
                self.refs_path_edit.setText(refs_path)
                self.no_refs_checkbox.setChecked(False)

            # Load basic data
            self.sample_edit.setText(data.get("sample", ""))
            self.setting_combo.setCurrentText(data.get("setting", "Standard"))
            self.stage_edit.setText(data.get("stage", ""))
            self.control_file_edit.setText(data.get("control_file", ""))
            self.mask_file_edit.setText(data.get("mask_file", ""))
            self.exposure_edit.setText(data.get("exposure", ""))
            self.step_spin.setValue(data.get("step", 1))
            self.spacing_spin.setValue(data.get("spacing", 5))
            self.frame_start_spin.setValue(data.get("frame_start", 0))
            self.frame_end_spin.setValue(data.get("frame_end", -1))
            self.az_start_spin.setValue(data.get("az_start", -110))
            self.az_end_spin.setValue(data.get("az_end", 110))
            self.notes_edit.setPlainText(data.get("notes", ""))

            # Load detector parameters
            detector_params = data.get("detector_params", {})
            pixel_size = detector_params.get("pixel_size", [172.0, 172.0])
            detector_size = detector_params.get("detector_size", [1475, 1679])
            self.pixel_x_spin.setValue(pixel_size[0])
            self.pixel_y_spin.setValue(pixel_size[1])
            self.wavelength_spin.setValue(detector_params.get("wavelength", 0.240))
            self.detector_x_spin.setValue(detector_size[0])
            self.detector_y_spin.setValue(detector_size[1])

            # Load calibration configuration
            calibration_config = data.get("calibration", {})
            auto_calibrate = calibration_config.get("auto_calibrate", False)
            self.auto_calibrate_checkbox.setChecked(auto_calibrate)
            if auto_calibrate:
                self.ceria_folder_edit.setText(calibration_config.get("ceria_folder", ""))
                self.calibrant_combo.setCurrentText(calibration_config.get("calibrant", "CeO2"))
                initial_params = calibration_config.get("initial_params", {})
                center = initial_params.get("center", [detector_size[0]/2.0, detector_size[1]/2.0])
                self.beam_center_x_spin.setValue(center[0])
                self.beam_center_y_spin.setValue(center[1])

            # Load peaks
            for peak_data in data.get("active_peaks", []):
                self.add_peak(peak_data)

            QMessageBox.information(self, "Success", "Recipe loaded successfully.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load recipe:\n{str(e)}")

    def remove_peak_force(self, peak_widget):
        """Force remove a peak widget without validation."""
        if peak_widget in self.peak_widgets:
            self.peak_widgets.remove(peak_widget)
            self.peaks_layout.removeWidget(peak_widget)
            peak_widget.deleteLater()

    def clear_form(self):
        """Clear the form and reset to defaults."""
        # Clear existing peaks
        for widget in self.peak_widgets[:]:
            self.remove_peak_force(widget)

        # Reset to defaults
        self.load_defaults()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look

    window = RecipeBuilder()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()