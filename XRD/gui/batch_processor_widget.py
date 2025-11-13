"""
Batch Processor GUI Widget
===========================
Visual interface for batch processing XRD recipes with real-time progress tracking.

Features:
- Recipe list with checkboxes for selection
- Real-time status indicators (Queued, Running, Done, Error)
- Progress bar showing current progress
- Log viewer for processing output
- Background processing to keep GUI responsive
"""

import os
import glob
import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QProgressBar,
    QSplitter, QGroupBox, QCheckBox, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QFont


class BatchProcessorThread(QThread):
    """
    Background thread for batch processing recipes.
    Emits signals to update GUI during processing.
    """

    # Signals for GUI updates
    progress_update = pyqtSignal(str, str, int, int)  # recipe_name, status, current, total
    log_message = pyqtSignal(str)  # log message
    processing_complete = pyqtSignal(int, int)  # success_count, error_count

    def __init__(self, recipe_files, workspace_path, move_recipes=True):
        """
        Initialize batch processor thread.

        Args:
            recipe_files: List of recipe file paths to process
            workspace_path: Workspace directory path
            move_recipes: Move recipes to processed/ after success
        """
        super().__init__()
        self.recipe_files = recipe_files
        self.workspace_path = workspace_path
        self.move_recipes = move_recipes
        self._is_running = True

    def run(self):
        """Execute batch processing in background thread."""
        from XRD.processing.recipes import load_recipe_from_file
        from XRD.processing import data_generator
        from XRD.utils.path_manager import get_processed_recipes_path
        import time
        import shutil

        total_recipes = len(self.recipe_files)
        success_count = 0
        error_count = 0

        processed_dir = get_processed_recipes_path(self.workspace_path)
        os.makedirs(processed_dir, exist_ok=True)

        self.log_message.emit(f"Starting batch processing of {total_recipes} recipes...")
        self.log_message.emit("=" * 60)

        for i, recipe_file in enumerate(self.recipe_files):
            if not self._is_running:
                self.log_message.emit("\nBatch processing cancelled by user.")
                break

            recipe_name = os.path.basename(recipe_file)

            # Update status to "Running"
            self.progress_update.emit(recipe_name, "Running", i + 1, total_recipes)
            self.log_message.emit(f"\n[{i+1}/{total_recipes}] Processing: {recipe_name}")

            try:
                # Load recipe
                recipe_data = load_recipe_from_file(recipe_file)

                self.log_message.emit(f"   Sample: {recipe_data.get('sample', 'Unknown')}")
                self.log_message.emit(f"   Setting: {recipe_data.get('setting', 'Unknown')}")
                self.log_message.emit(f"   Stage: {recipe_data.get('stage', 'Unknown')}")
                self.log_message.emit(f"   Peaks: {len(recipe_data.get('active_peaks', []))}")

                # Process the recipe
                start_time = time.time()
                dataset = data_generator.generate_data_from_recipe(recipe_data, recipe_name, client=None)
                processing_time = time.time() - start_time

                if dataset:
                    self.log_message.emit(f"   Success! Generated dataset in {processing_time:.1f}s")
                    self.log_message.emit(f"   Shape: {dataset.data.shape}")

                    # Verify save path
                    save_path = dataset.params.save_path()
                    if os.path.exists(save_path):
                        self.log_message.emit(f"   Zarr file verified: {os.path.basename(save_path)}")
                    else:
                        self.log_message.emit(f"   WARNING: Zarr file not found!")

                    # Move recipe to processed directory
                    if self.move_recipes:
                        processed_file = os.path.join(processed_dir, recipe_name)
                        shutil.move(recipe_file, processed_file)
                        self.log_message.emit(f"   Moved recipe to processed/")

                    # Update status to "Done"
                    self.progress_update.emit(recipe_name, "Done", i + 1, total_recipes)
                    success_count += 1

                else:
                    self.log_message.emit(f"   Dataset generation failed")
                    self.progress_update.emit(recipe_name, "Error", i + 1, total_recipes)
                    error_count += 1

            except Exception as e:
                self.log_message.emit(f"   Error: {str(e)}")
                self.progress_update.emit(recipe_name, "Error", i + 1, total_recipes)
                error_count += 1

        # Processing complete
        self.log_message.emit("\n" + "=" * 60)
        self.log_message.emit(f"Batch processing complete!")
        self.log_message.emit(f"   Success: {success_count}")
        self.log_message.emit(f"   Errors: {error_count}")
        self.log_message.emit("=" * 60)

        self.processing_complete.emit(success_count, error_count)

    def stop(self):
        """Stop batch processing gracefully."""
        self._is_running = False


class BatchProcessorWidget(QWidget):
    """
    GUI widget for batch processing XRD recipes.

    Provides visual interface with:
    - Recipe selection list
    - Real-time status indicators
    - Progress tracking
    - Log output viewer
    """

    def __init__(self, workspace_path=None, parent=None):
        """
        Initialize batch processor widget.

        Args:
            workspace_path: Workspace directory path
            parent: Parent widget
        """
        super().__init__(parent)
        self.workspace_path = workspace_path
        self.recipe_items = {}  # Map recipe_name -> QListWidgetItem
        self.processor_thread = None
        self.init_ui()

        # Load recipes if workspace is set
        if workspace_path:
            self.load_recipes()

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()

        # Title
        title_label = QLabel("Batch Recipe Processor")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Main splitter (recipe list | log viewer)
        splitter = QSplitter(Qt.Horizontal)

        # Left panel: Recipe list
        left_panel = QWidget()
        left_layout = QVBoxLayout()

        # Recipe list group
        recipe_group = QGroupBox("Recipes")
        recipe_layout = QVBoxLayout()

        self.recipe_list = QListWidget()
        self.recipe_list.setSelectionMode(QListWidget.MultiSelection)
        recipe_layout.addWidget(self.recipe_list)

        # Select all/none buttons
        selection_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_recipes)
        selection_layout.addWidget(select_all_btn)

        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self.select_no_recipes)
        selection_layout.addWidget(select_none_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_recipes)
        selection_layout.addWidget(refresh_btn)

        recipe_layout.addLayout(selection_layout)
        recipe_group.setLayout(recipe_layout)
        left_layout.addWidget(recipe_group)

        # Progress group
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)

        progress_group.setLayout(progress_layout)
        left_layout.addWidget(progress_group)

        # Control buttons
        control_layout = QHBoxLayout()

        self.run_button = QPushButton("Run Batch Processing")
        self.run_button.clicked.connect(self.start_processing)
        self.run_button.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; }")
        control_layout.addWidget(self.run_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_processing)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)

        left_layout.addLayout(control_layout)

        # Move recipes checkbox
        self.move_recipes_checkbox = QCheckBox("Move recipes to processed/ after success")
        self.move_recipes_checkbox.setChecked(True)
        left_layout.addWidget(self.move_recipes_checkbox)

        left_panel.setLayout(left_layout)
        splitter.addWidget(left_panel)

        # Right panel: Log viewer
        right_panel = QWidget()
        right_layout = QVBoxLayout()

        log_group = QGroupBox("Processing Log")
        log_layout = QVBoxLayout()

        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setFont(QFont("Courier", 9))
        log_layout.addWidget(self.log_viewer)

        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.log_viewer.clear)
        log_layout.addWidget(clear_log_btn)

        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)

        right_panel.setLayout(right_layout)
        splitter.addWidget(right_panel)

        # Set initial splitter sizes (40% left, 60% right)
        splitter.setSizes([400, 600])

        layout.addWidget(splitter)
        self.setLayout(layout)

    def set_workspace(self, workspace_path):
        """
        Set workspace directory and reload recipes.

        Args:
            workspace_path: Path to workspace directory
        """
        self.workspace_path = workspace_path
        self.load_recipes()

    def load_recipes(self):
        """Load recipe files from workspace recipes/ directory."""
        self.recipe_list.clear()
        self.recipe_items.clear()

        if not self.workspace_path:
            self.log_viewer.append("No workspace selected. Please select a workspace first.")
            return

        from XRD.utils.path_manager import get_recipes_path

        recipe_dir = get_recipes_path(self.workspace_path)

        if not os.path.exists(recipe_dir):
            self.log_viewer.append(f"Recipe directory not found: {recipe_dir}")
            self.log_viewer.append("Creating directory...")
            os.makedirs(recipe_dir, exist_ok=True)
            return

        # Find all JSON files
        recipe_files = glob.glob(os.path.join(recipe_dir, "*.json"))

        if not recipe_files:
            self.log_viewer.append(f"No recipe files found in {recipe_dir}/")
            self.log_viewer.append("Use Recipe Builder to create recipes.")
            return

        # Add recipes to list
        for recipe_file in sorted(recipe_files):
            recipe_name = os.path.basename(recipe_file)
            item = QListWidgetItem(f"⚪ {recipe_name}")
            item.setData(Qt.UserRole, recipe_file)  # Store full path
            self.recipe_list.addItem(item)
            self.recipe_items[recipe_name] = item

        self.log_viewer.append(f"Loaded {len(recipe_files)} recipes from {recipe_dir}")

    def select_all_recipes(self):
        """Select all recipes in the list."""
        for i in range(self.recipe_list.count()):
            self.recipe_list.item(i).setSelected(True)

    def select_no_recipes(self):
        """Deselect all recipes in the list."""
        for i in range(self.recipe_list.count()):
            self.recipe_list.item(i).setSelected(False)

    def start_processing(self):
        """Start batch processing of selected recipes."""
        # Get selected recipes
        selected_items = self.recipe_list.selectedItems()

        if not selected_items:
            QMessageBox.warning(
                self,
                "No Recipes Selected",
                "Please select at least one recipe to process."
            )
            return

        if not self.workspace_path:
            QMessageBox.warning(
                self,
                "No Workspace",
                "Please select a workspace directory first."
            )
            return

        # Get recipe file paths
        recipe_files = [item.data(Qt.UserRole) for item in selected_items]

        # Update UI state
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(recipe_files))
        self.status_label.setText(f"Processing 0 of {len(recipe_files)}...")
        self.log_viewer.clear()

        # Mark all selected as "Queued"
        for item in selected_items:
            recipe_name = os.path.basename(item.data(Qt.UserRole))
            item.setText(f"⚪ {recipe_name}")
            item.setForeground(QColor("gray"))

        # Start processing thread
        move_recipes = self.move_recipes_checkbox.isChecked()
        self.processor_thread = BatchProcessorThread(recipe_files, self.workspace_path, move_recipes)
        self.processor_thread.progress_update.connect(self.on_progress_update)
        self.processor_thread.log_message.connect(self.on_log_message)
        self.processor_thread.processing_complete.connect(self.on_processing_complete)
        self.processor_thread.start()

    def stop_processing(self):
        """Stop batch processing."""
        if self.processor_thread and self.processor_thread.isRunning():
            self.processor_thread.stop()
            self.log_viewer.append("\n[Stopping batch processing...]")
            self.stop_button.setEnabled(False)

    @pyqtSlot(str, str, int, int)
    def on_progress_update(self, recipe_name, status, current, total):
        """
        Handle progress update from processing thread.

        Args:
            recipe_name: Name of recipe being processed
            status: Status string ("Running", "Done", "Error")
            current: Current recipe number (1-indexed)
            total: Total number of recipes
        """
        # Update progress bar
        self.progress_bar.setValue(current)
        self.status_label.setText(f"Processing {current} of {total}...")

        # Update recipe list item
        if recipe_name in self.recipe_items:
            item = self.recipe_items[recipe_name]

            if status == "Running":
                item.setText(f"🟡 {recipe_name}")
                item.setForeground(QColor("orange"))
            elif status == "Done":
                item.setText(f"🟢 {recipe_name}")
                item.setForeground(QColor("green"))
            elif status == "Error":
                item.setText(f"🔴 {recipe_name}")
                item.setForeground(QColor("red"))

    @pyqtSlot(str)
    def on_log_message(self, message):
        """
        Handle log message from processing thread.

        Args:
            message: Log message string
        """
        self.log_viewer.append(message)

        # Auto-scroll to bottom
        scrollbar = self.log_viewer.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @pyqtSlot(int, int)
    def on_processing_complete(self, success_count, error_count):
        """
        Handle processing completion.

        Args:
            success_count: Number of successful recipes
            error_count: Number of failed recipes
        """
        # Update UI state
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText(f"Complete! Success: {success_count}, Errors: {error_count}")

        # Show completion message
        QMessageBox.information(
            self,
            "Batch Processing Complete",
            f"Processing finished!\n\n"
            f"Success: {success_count}\n"
            f"Errors: {error_count}"
        )

        # Reload recipe list (successful recipes may have been moved)
        self.load_recipes()


if __name__ == "__main__":
    # Test the batch processor widget
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    widget = BatchProcessorWidget()
    widget.resize(1000, 600)
    widget.show()

    sys.exit(app.exec_())
