"""
PRISMA Main Launcher
====================
Unified launcher application with tabbed interface for all PRISMA functionality.

Features:
- Tab 1: Recipe Builder - Create XRD processing recipes
- Tab 2: Batch Processor - Process multiple recipes with progress tracking
- Tab 3: Data Analyzer - Visualize and analyze XRD datasets
- File menu: Workspace selection and settings
- Tools menu: Check for updates
- Help menu: About dialog and documentation
"""

import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QAction, QMessageBox,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextBrowser
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont

# Import version
from XRD import __version__

# Import utility modules
from XRD.utils.config_manager import get_config_manager
from XRD.utils.update_checker import check_for_updates
from XRD.gui.workspace_dialog import select_workspace
from XRD.gui.batch_processor_widget import BatchProcessorWidget


class UpdateCheckThread(QThread):
    """Background thread for checking updates without blocking GUI."""

    update_found = pyqtSignal(dict)  # Emits update info dict
    no_update = pyqtSignal()  # Emits when no update available
    error = pyqtSignal(str)  # Emits error message

    def __init__(self, force=False):
        super().__init__()
        self.force = force

    def run(self):
        """Check for updates in background."""
        try:
            update_info = check_for_updates(force=self.force)
            if update_info and update_info.get('update_available'):
                self.update_found.emit(update_info)
            else:
                self.no_update.emit()
        except Exception as e:
            self.error.emit(str(e))


class UpdateDialog(QDialog):
    """Dialog to notify user about available updates."""

    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.init_ui()

    def init_ui(self):
        """Initialize update dialog UI."""
        self.setWindowTitle("PRISMA Update Available")
        self.setModal(True)
        self.setMinimumWidth(500)

        layout = QVBoxLayout()

        # Title
        title_label = QLabel("🎉 PRISMA Update Available!")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Version info
        current_version = self.update_info.get('current_version', 'Unknown')
        latest_version = self.update_info.get('latest_version', 'Unknown')

        version_text = (
            f"<p><b>Current version:</b> {current_version}<br>"
            f"<b>Latest version:</b> {latest_version}</p>"
        )
        version_label = QLabel(version_text)
        layout.addWidget(version_label)

        # Release notes link
        release_url = self.update_info.get('release_notes_url', '')
        if release_url:
            notes_text = f'<p>View release notes:<br><a href="{release_url}">{release_url}</a></p>'
            notes_label = QLabel(notes_text)
            notes_label.setOpenExternalLinks(True)
            notes_label.setWordWrap(True)
            layout.addWidget(notes_label)

        # Download button
        download_url = self.update_info.get('download_url')
        if download_url:
            download_btn = QPushButton("Download Update")
            download_btn.clicked.connect(lambda: self.open_download(download_url))
            layout.addWidget(download_btn)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Remind Me Later")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        # Opt-out checkbox handled separately if needed

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def open_download(self, url):
        """Open download URL in browser."""
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(url))
        self.accept()


class AboutDialog(QDialog):
    """About dialog with PRISMA information."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize about dialog UI."""
        self.setWindowTitle("About PRISMA")
        self.setModal(True)
        self.setMinimumWidth(500)

        layout = QVBoxLayout()

        # Title
        title_label = QLabel("PRISMA")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel(
            "Parallel Refinement and Integration System<br>"
            "for Multi-Azimuthal Analysis"
        )
        subtitle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle_label)

        # Version
        version_label = QLabel(f"Version {__version__}")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        # Description
        description = QTextBrowser()
        description.setOpenExternalLinks(True)
        description.setHtml(f"""
            <p>A Python-based X-ray diffraction (XRD) data processing system for materials science analysis.</p>

            <p><b>Features:</b></p>
            <ul>
                <li>Recipe-based XRD data processing</li>
                <li>GSAS-II integration for peak fitting</li>
                <li>Multi-frame image support (TIFF, EDF, GE5)</li>
                <li>HPC deployment with Dask-MPI</li>
                <li>Advanced compression and optimization</li>
                <li>Strain analysis and visualization</li>
            </ul>

            <p><b>Authors:</b> William Gonzalez, Adrian Guzman, Luke Davenport</p>

            <p><b>Links:</b></p>
            <ul>
                <li><a href="https://github.com/wdgonzo/PRISMA">GitHub Repository</a></li>
                <li><a href="https://github.com/wdgonzo/PRISMA/issues">Bug Tracker</a></li>
            </ul>

            <p><i>PRISMA uses GSAS-II for peak fitting. GSAS-II must be installed separately.</i></p>
        """)
        layout.addWidget(description)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)


class MainLauncher(QMainWindow):
    """
    Main PRISMA launcher window with tabbed interface.

    Provides unified access to:
    - Recipe Builder (Tab 1)
    - Batch Processor (Tab 2)
    - Data Analyzer (Tab 3)

    Plus menu bar for workspace settings and updates.
    """

    def __init__(self):
        super().__init__()
        self.config = get_config_manager()
        self.init_ui()

        # Check for workspace on first launch
        if self.config.is_first_launch():
            self.show_first_launch_wizard()

        # Check for updates (non-blocking)
        if self.config.should_check_updates():
            self.check_for_updates_background()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle(f"PRISMA v{__version__}")
        self.setMinimumSize(1200, 800)

        # Restore window geometry if available
        geometry = self.config.get_window_geometry()
        if geometry:
            self.setGeometry(
                geometry['x'],
                geometry['y'],
                geometry['width'],
                geometry['height']
            )
        else:
            # Center window on screen
            self.center_on_screen()

        # Create menu bar
        self.create_menu_bar()

        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setMovable(False)

        # Create tabs (simplified for now - will integrate full widgets later)
        self.create_recipe_builder_tab()
        self.create_batch_processor_tab()
        self.create_data_analyzer_tab()

        self.setCentralWidget(self.tabs)

        # Status bar
        self.statusBar().showMessage("Ready")

        # Update workspace-dependent tabs
        self.update_workspace_status()

    def center_on_screen(self):
        """Center window on screen."""
        screen = QApplication.desktop().screenGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )

    def create_menu_bar(self):
        """Create application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        workspace_action = QAction("Select &Workspace...", self)
        workspace_action.setShortcut("Ctrl+W")
        workspace_action.setStatusTip("Select workspace directory")
        workspace_action.triggered.connect(self.select_workspace)
        file_menu.addAction(workspace_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        update_action = QAction("Check for &Updates", self)
        update_action.setStatusTip("Check for PRISMA updates")
        update_action.triggered.connect(self.check_for_updates_manual)
        tools_menu.addAction(update_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        docs_action = QAction("&Documentation", self)
        docs_action.setShortcut("F1")
        docs_action.setStatusTip("Open documentation")
        docs_action.triggered.connect(self.open_documentation)
        help_menu.addAction(docs_action)

        help_menu.addSeparator()

        about_action = QAction("&About PRISMA", self)
        about_action.setStatusTip("About PRISMA")
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def create_recipe_builder_tab(self):
        """Create Recipe Builder tab (placeholder for now)."""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

        tab = QWidget()
        layout = QVBoxLayout()

        label = QLabel("Recipe Builder\n\n(Integration pending - use run_recipe_builder.py for now)")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Recipe Builder")

    def create_batch_processor_tab(self):
        """Create Batch Processor tab with real widget."""
        workspace = self.config.get_workspace_path()
        self.batch_processor_widget = BatchProcessorWidget(workspace_path=workspace)
        self.tabs.addTab(self.batch_processor_widget, "Batch Processor")

    def create_data_analyzer_tab(self):
        """Create Data Analyzer tab (placeholder for now)."""
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

        tab = QWidget()
        layout = QVBoxLayout()

        label = QLabel("Data Analyzer\n\n(Integration pending - use run_data_analyzer.py for now)")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Data Analyzer")

    def show_first_launch_wizard(self):
        """Show first-launch workspace setup wizard."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Welcome to PRISMA")
        msg.setText("Welcome to PRISMA!\n\nLet's set up your workspace directory.")
        msg.setInformativeText(
            "The workspace contains your data, processed results, and recipes.\n\n"
            "Would you like to select a workspace now?"
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)

        result = msg.exec_()

        if result == QMessageBox.Yes:
            self.select_workspace()
        else:
            # Remind user to set workspace later
            self.statusBar().showMessage("Please select a workspace (File → Select Workspace)", 10000)

        # Mark first launch complete
        self.config.set_first_launch_complete()

    def select_workspace(self):
        """Open workspace selection dialog."""
        current_workspace = self.config.get_workspace_path()
        new_workspace = select_workspace(current_workspace, self)

        if new_workspace:
            self.config.set_workspace_path(new_workspace)
            self.update_workspace_status()
            self.statusBar().showMessage(f"Workspace set to: {new_workspace}", 5000)

    def update_workspace_status(self):
        """Update workspace-dependent UI elements."""
        workspace = self.config.get_workspace_path()

        # Update batch processor widget
        if hasattr(self, 'batch_processor_widget'):
            self.batch_processor_widget.set_workspace(workspace)

        # Update window title to show workspace
        if workspace:
            self.setWindowTitle(f"PRISMA v{__version__} - {Path(workspace).name}")
        else:
            self.setWindowTitle(f"PRISMA v{__version__} - No Workspace")

    def check_for_updates_background(self):
        """Check for updates in background (non-blocking)."""
        self.update_thread = UpdateCheckThread(force=False)
        self.update_thread.update_found.connect(self.show_update_dialog)
        # Silently ignore no_update and error for background checks
        self.update_thread.start()

    def check_for_updates_manual(self):
        """Check for updates manually (user-initiated)."""
        self.statusBar().showMessage("Checking for updates...")

        self.update_thread = UpdateCheckThread(force=True)
        self.update_thread.update_found.connect(self.show_update_dialog)
        self.update_thread.no_update.connect(self.show_no_update_message)
        self.update_thread.error.connect(self.show_update_error)
        self.update_thread.start()

    def show_update_dialog(self, update_info):
        """Show update dialog when update is available."""
        dialog = UpdateDialog(update_info, self)
        dialog.exec_()
        self.statusBar().showMessage("Update available!")

    def show_no_update_message(self):
        """Show message when no update is available (manual check)."""
        QMessageBox.information(
            self,
            "No Updates",
            f"PRISMA is up to date!\n\nCurrent version: {__version__}"
        )
        self.statusBar().showMessage("PRISMA is up to date")

    def show_update_error(self, error_msg):
        """Show error message if update check fails."""
        QMessageBox.warning(
            self,
            "Update Check Failed",
            f"Could not check for updates:\n\n{error_msg}\n\n"
            "Please check your internet connection."
        )
        self.statusBar().showMessage("Update check failed")

    def open_documentation(self):
        """Open documentation in browser."""
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl

        docs_url = "https://github.com/wdgonzo/PRISMA/blob/main/README.md"
        QDesktopServices.openUrl(QUrl(docs_url))

    def show_about_dialog(self):
        """Show about dialog."""
        dialog = AboutDialog(self)
        dialog.exec_()

    def closeEvent(self, event):
        """Handle window close event - save geometry."""
        # Save window geometry
        geometry = self.geometry()
        self.config.set_window_geometry(
            geometry.x(),
            geometry.y(),
            geometry.width(),
            geometry.height()
        )

        event.accept()


def main():
    """Main entry point for PRISMA launcher."""
    app = QApplication(sys.argv)
    app.setApplicationName("PRISMA")
    app.setApplicationVersion(__version__)

    launcher = MainLauncher()
    launcher.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
