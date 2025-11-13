"""
Workspace Selection Dialog
===========================
Dialog for selecting and managing PRISMA workspace directory.

The workspace contains:
- Images/ - Raw diffraction images
- Processed/ - Processed Zarr datasets
- Analysis/ - Analysis outputs (heatmaps, CSVs)
- recipes/ - Processing recipe JSON files
"""

import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QCheckBox, QMessageBox, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class WorkspaceDialog(QDialog):
    """
    Dialog for workspace directory selection.

    Allows users to:
    - Browse for workspace directory
    - Create standard directory structure
    - Validate workspace configuration
    """

    def __init__(self, current_workspace=None, parent=None):
        """
        Initialize workspace selection dialog.

        Args:
            current_workspace: Currently configured workspace path (if any)
            parent: Parent widget
        """
        super().__init__(parent)
        self.workspace_path = current_workspace
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("PRISMA Workspace Selection")
        self.setModal(True)
        self.setMinimumWidth(600)

        layout = QVBoxLayout()

        # Title and description
        title_label = QLabel("Select PRISMA Workspace Directory")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        description = QLabel(
            "The workspace directory contains your data, processed results, and recipes.\n"
            "PRISMA will create the following subdirectories if they don't exist:"
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        # Directory structure info
        structure_group = QGroupBox("Workspace Structure")
        structure_layout = QVBoxLayout()

        structure_text = """
• Images/     - Raw diffraction images (.tif, .edf, .edf.GE5)
• Processed/  - Processed Zarr datasets
• Analysis/   - Analysis outputs (heatmaps, CSV files)
• recipes/    - Processing recipe JSON files
        """
        structure_label = QLabel(structure_text)
        structure_label.setStyleSheet("font-family: monospace;")
        structure_layout.addWidget(structure_label)
        structure_group.setLayout(structure_layout)
        layout.addWidget(structure_group)

        # Workspace selection
        workspace_layout = QHBoxLayout()
        workspace_label = QLabel("Workspace:")
        workspace_label.setMinimumWidth(100)
        workspace_layout.addWidget(workspace_label)

        self.workspace_edit = QLineEdit()
        if self.workspace_path:
            self.workspace_edit.setText(self.workspace_path)
        else:
            # Default to Documents/PRISMA
            default_path = str(Path.home() / "Documents" / "PRISMA")
            self.workspace_edit.setText(default_path)
        workspace_layout.addWidget(self.workspace_edit)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_workspace)
        workspace_layout.addWidget(browse_button)

        layout.addLayout(workspace_layout)

        # Create directories checkbox
        self.create_dirs_checkbox = QCheckBox("Create standard directory structure")
        self.create_dirs_checkbox.setChecked(True)
        layout.addWidget(self.create_dirs_checkbox)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept_workspace)
        self.ok_button.setDefault(True)
        button_layout.addWidget(self.ok_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def browse_workspace(self):
        """Open directory browser for workspace selection."""
        current = self.workspace_edit.text()
        if not current or not os.path.exists(current):
            current = str(Path.home() / "Documents")

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Workspace Directory",
            current,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if directory:
            self.workspace_edit.setText(directory)

    def accept_workspace(self):
        """Validate and accept workspace selection."""
        workspace_path = self.workspace_edit.text().strip()

        if not workspace_path:
            QMessageBox.warning(
                self,
                "Invalid Workspace",
                "Please select a workspace directory."
            )
            return

        # Convert to absolute path
        workspace_path = os.path.abspath(workspace_path)

        # Check if directory exists
        if not os.path.exists(workspace_path):
            # Ask user if they want to create it
            reply = QMessageBox.question(
                self,
                "Create Directory",
                f"The directory does not exist:\n\n{workspace_path}\n\n"
                "Do you want to create it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                try:
                    os.makedirs(workspace_path, exist_ok=True)
                except OSError as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Could not create directory:\n\n{e}"
                    )
                    return
            else:
                return

        # Create standard directories if requested
        if self.create_dirs_checkbox.isChecked():
            subdirs = ['Images', 'Processed', 'Analysis', 'recipes']
            created_dirs = []

            for subdir in subdirs:
                subdir_path = os.path.join(workspace_path, subdir)
                try:
                    os.makedirs(subdir_path, exist_ok=True)
                    if not os.path.exists(subdir_path):  # Just created
                        created_dirs.append(subdir)
                except OSError as e:
                    QMessageBox.warning(
                        self,
                        "Warning",
                        f"Could not create directory '{subdir}':\n\n{e}"
                    )

            if created_dirs:
                QMessageBox.information(
                    self,
                    "Directories Created",
                    f"Created workspace subdirectories:\n\n" +
                    "\n".join(f"• {d}" for d in created_dirs)
                )

        # Store workspace path and accept dialog
        self.workspace_path = workspace_path
        self.accept()

    def get_workspace_path(self):
        """
        Get selected workspace path.

        Returns:
            Absolute path to workspace directory or None if cancelled
        """
        return self.workspace_path


def select_workspace(current_workspace=None, parent=None):
    """
    Show workspace selection dialog and return selected path.

    Args:
        current_workspace: Currently configured workspace path
        parent: Parent widget

    Returns:
        Selected workspace path or None if cancelled
    """
    dialog = WorkspaceDialog(current_workspace, parent)
    result = dialog.exec_()

    if result == QDialog.Accepted:
        return dialog.get_workspace_path()
    return None


if __name__ == "__main__":
    # Test the workspace dialog
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    workspace = select_workspace()

    if workspace:
        print(f"Selected workspace: {workspace}")
    else:
        print("Workspace selection cancelled")

    sys.exit(0)
