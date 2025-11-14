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
    QSplitter, QGroupBox, QCheckBox, QMessageBox, QDialog, QSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QFont


class LogPopupDialog(QDialog):
    """
    Popup terminal window for displaying processing logs in real-time.

    Features:
    - Detachable window that can be minimized
    - Auto-scrolling log output
    - Monospace font for terminal-like appearance
    - Can stay open after processing completes
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PRISMA Batch Processing Log")
        self.setGeometry(150, 150, 800, 600)

        # Layout
        layout = QVBoxLayout()

        # Log viewer
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setFont(QFont("Courier", 9))
        self.log_viewer.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")  # Dark terminal theme
        layout.addWidget(self.log_viewer)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def append_log(self, message):
        """Append message to log and auto-scroll to bottom."""
        self.log_viewer.append(message)

        # Auto-scroll to bottom
        scrollbar = self.log_viewer.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log(self):
        """Clear all log content."""
        self.log_viewer.clear()


class FileAndSignalCapture:
    """
    Captures stdout/stderr output and writes to BOTH log file AND signal.

    Used to redirect Python's print() statements and library output
    to both a persistent log file and the terminal popup.
    """

    def __init__(self, signal, log_file):
        """
        Initialize output capture.

        Args:
            signal: PyQt signal to emit captured text to
            log_file: Open file object to write logs to
        """
        self.signal = signal
        self.log_file = log_file

    def write(self, text):
        """Write text to both file and signal (called by print())."""
        if text.strip():  # Skip empty lines
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            logged_text = f"[{timestamp}] {text.rstrip()}"

            # Write to file with timestamp
            if self.log_file:
                self.log_file.write(logged_text + "\n")
                self.log_file.flush()  # Immediate flush

            # Emit to signal (without timestamp for cleaner GUI display)
            self.signal.emit(text.rstrip())

    def flush(self):
        """Flush buffer (required for file-like interface)."""
        if self.log_file:
            self.log_file.flush()


class BatchProcessorThread(QThread):
    """
    Background thread for batch processing recipes.
    Emits signals to update GUI during processing.
    """

    # Signals for GUI updates
    progress_update = pyqtSignal(str, str, int, int)  # recipe_name, status, current, total
    log_message = pyqtSignal(str)  # High-level GUI progress messages
    terminal_output = pyqtSignal(str)  # Raw stdout/stderr from processing
    processing_complete = pyqtSignal(int, int)  # success_count, error_count

    def __init__(self, recipe_files, workspace_path, move_recipes=True, capture_output=False, n_workers=None):
        """
        Initialize batch processor thread.

        Args:
            recipe_files: List of recipe file paths to process
            workspace_path: Workspace directory path
            move_recipes: Move recipes to processed/ after success
            capture_output: Capture stdout/stderr for terminal popup
            n_workers: Number of Dask workers to use (None = auto-detect)
        """
        print(f"DEBUG: BatchProcessorThread.__init__ called with {len(recipe_files)} recipes")
        super().__init__()
        self.recipe_files = recipe_files
        self.workspace_path = workspace_path
        self.move_recipes = move_recipes
        self.capture_output = capture_output
        self.n_workers = n_workers
        self._is_running = True
        print("DEBUG: BatchProcessorThread.__init__ completed")

    def run(self):
        """Execute batch processing in background thread."""
        import sys
        print(f"DEBUG: run() method started", file=sys.__stdout__)
        sys.__stdout__.flush()

        from XRD.processing.recipes import load_recipe_from_file
        from XRD.processing import data_generator
        from XRD.utils.path_manager import get_processed_recipes_path
        from XRD.hpc.cluster import get_dask_client, close_dask_client
        from datetime import datetime
        from pathlib import Path
        import time
        import shutil
        import traceback

        print(f"DEBUG: Imports completed", file=sys.__stdout__)
        sys.__stdout__.flush()

        # Create log file in ~/.prisma/logs/
        print(f"DEBUG: Creating log file", file=sys.__stdout__)
        sys.__stdout__.flush()

        log_dir = Path.home() / '.prisma' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = log_dir / f"batch_processing_{timestamp}.log"
        log_file = open(log_file_path, 'w', encoding='utf-8')

        print(f"DEBUG: Log file created: {log_file_path}", file=sys.__stdout__)
        sys.__stdout__.flush()

        # Log file header
        log_file.write(f"="*80 + "\n")
        log_file.write(f"PRISMA Batch Processing Log\n")
        log_file.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"Recipes: {len(self.recipe_files)}\n")
        log_file.write(f"Workers: {self.n_workers or 'auto'}\n")
        log_file.write(f"="*80 + "\n\n")
        log_file.flush()

        # Emit log file location to GUI
        self.log_message.emit(f"Full log: {log_file_path}")
        self.log_message.emit("")

        # Setup stdout/stderr capture to BOTH file and signal
        original_stdout = None
        original_stderr = None
        if self.capture_output:
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            sys.stdout = FileAndSignalCapture(self.terminal_output, log_file)
            sys.stderr = FileAndSignalCapture(self.terminal_output, log_file)
        else:
            # Even without terminal, capture to file for debugging
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            sys.stdout = FileAndSignalCapture(self.terminal_output, log_file)
            sys.stderr = FileAndSignalCapture(self.terminal_output, log_file)

        # Create shared Dask client for all recipes (more efficient than per-recipe)
        dask_client = None

        try:
            log_file.write(f"[{datetime.now().strftime('%H:%M:%S')}] Thread started\n")
            log_file.flush()

            total_recipes = len(self.recipe_files)
            success_count = 0
            error_count = 0

            processed_dir = get_processed_recipes_path(self.workspace_path)
            os.makedirs(processed_dir, exist_ok=True)

            self.log_message.emit(f"Starting batch processing of {total_recipes} recipes...")
            self.log_message.emit("=" * 60)

            # Initialize Dask client once for all recipes
            print(f"DEBUG: About to call get_dask_client()", file=sys.__stdout__)
            sys.__stdout__.flush()

            log_file.write(f"[{datetime.now().strftime('%H:%M:%S')}] Initializing Dask cluster...\n")
            log_file.flush()
            self.log_message.emit(f"Initializing Dask cluster with {self.n_workers or 'auto'} workers...")

            dask_client = get_dask_client(n_workers=self.n_workers, verbose=True)

            print(f"DEBUG: get_dask_client() returned successfully", file=sys.__stdout__)
            sys.__stdout__.flush()

            log_file.write(f"[{datetime.now().strftime('%H:%M:%S')}] Dask client created successfully\n")
            log_file.flush()
            self.log_message.emit(f"Dask client initialized successfully")

            completed_count = 0  # Track completed recipes for progress

            # Check if stop was requested before starting processing
            if not self._is_running:
                self.log_message.emit("\nBatch processing cancelled before start.")
                return

            for i, recipe_file in enumerate(self.recipe_files):
                if not self._is_running:
                    self.log_message.emit("\nBatch processing cancelled by user.")
                    break

                recipe_name = os.path.basename(recipe_file)

                # Log which recipe is being processed (no progress update yet)
                self.log_message.emit(f"\n[{i+1}/{total_recipes}] Processing: {recipe_name}")

                try:
                    # Load recipe
                    recipe_data = load_recipe_from_file(recipe_file)

                    self.log_message.emit(f"   Sample: {recipe_data.get('sample', 'Unknown')}")
                    self.log_message.emit(f"   Setting: {recipe_data.get('setting', 'Unknown')}")
                    self.log_message.emit(f"   Stage: {recipe_data.get('stage', 'Unknown')}")
                    self.log_message.emit(f"   Peaks: {len(recipe_data.get('active_peaks', []))}")

                    # Process the recipe
                    self.log_message.emit(f"   Starting data generation...")
                    start_time = time.time()
                    dataset = data_generator.generate_data_from_recipe(recipe_data, recipe_name, client=dask_client)
                    processing_time = time.time() - start_time
                    self.log_message.emit(f"   Data generation completed in {processing_time:.1f}s")

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

                        # Update status to "Done" - increment completed count THEN emit
                        completed_count += 1
                        self.progress_update.emit(recipe_name, "Done", completed_count, total_recipes)
                        success_count += 1

                    else:
                        self.log_message.emit(f"   Dataset generation failed")
                        completed_count += 1
                        self.progress_update.emit(recipe_name, "Error", completed_count, total_recipes)
                        error_count += 1

                except Exception as e:
                    error_msg = f"   Error: {str(e)}"
                    self.log_message.emit(error_msg)
                    # Log full traceback to file
                    log_file.write(f"\n[{datetime.now().strftime('%H:%M:%S')}] EXCEPTION:\n")
                    log_file.write(traceback.format_exc())
                    log_file.write("\n")
                    log_file.flush()
                    completed_count += 1
                    self.progress_update.emit(recipe_name, "Error", completed_count, total_recipes)
                    error_count += 1

            # Processing complete
            self.log_message.emit("\n" + "=" * 60)
            self.log_message.emit(f"Batch processing complete!")
            self.log_message.emit(f"   Success: {success_count}")
            self.log_message.emit(f"   Errors: {error_count}")
            self.log_message.emit("=" * 60)

            self.processing_complete.emit(success_count, error_count)

        except Exception as e:
            # Catch any unhandled exceptions
            error_msg = f"\nFATAL ERROR: {str(e)}"
            self.log_message.emit(error_msg)
            log_file.write(f"\n[{datetime.now().strftime('%H:%M:%S')}] FATAL EXCEPTION:\n")
            log_file.write(traceback.format_exc())
            log_file.write("\n")
            log_file.flush()

        finally:
            # Cleanup Dask client
            if dask_client is not None:
                log_file.write(f"[{datetime.now().strftime('%H:%M:%S')}] Closing Dask client...\n")
                log_file.flush()
                self.log_message.emit("\nClosing Dask cluster...")
                try:
                    close_dask_client(dask_client)
                    self.log_message.emit("Dask cluster closed")
                    log_file.write(f"[{datetime.now().strftime('%H:%M:%S')}] Dask client closed\n")
                except Exception as e:
                    log_file.write(f"[{datetime.now().strftime('%H:%M:%S')}] Error closing client: {e}\n")
                log_file.flush()

            # Restore stdout/stderr if they were redirected
            if original_stdout is not None:
                sys.stdout = original_stdout
            if original_stderr is not None:
                sys.stderr = original_stderr

            # Close log file
            log_file.write(f"\n[{datetime.now().strftime('%H:%M:%S')}] Thread finished\n")
            log_file.write(f"="*80 + "\n")
            log_file.close()
            self.log_message.emit(f"\nLog saved to: {log_file_path}")

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
        self.log_popup = None  # Log popup dialog
        self.init_ui()

        # Load recipes if workspace is set
        if workspace_path:
            self.load_recipes()

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()

        # Main splitter (recipe list | log viewer)
        splitter = QSplitter(Qt.Horizontal)

        # Left panel: Recipe list
        left_panel = QWidget()
        left_layout = QVBoxLayout()

        # Recipe list group
        recipe_group = QGroupBox("Recipes")
        recipe_layout = QVBoxLayout()

        self.recipe_list = QListWidget()
        self.recipe_list.setSelectionMode(QListWidget.NoSelection)  # Use checkboxes only, no row selection
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

        # Options checkboxes
        self.move_recipes_checkbox = QCheckBox("Move recipes to processed/ after success")
        self.move_recipes_checkbox.setChecked(True)
        left_layout.addWidget(self.move_recipes_checkbox)

        self.show_terminal_checkbox = QCheckBox("Show Processing Terminal (for debugging)")
        self.show_terminal_checkbox.setChecked(False)
        left_layout.addWidget(self.show_terminal_checkbox)

        # Worker cores selector
        cores_layout = QHBoxLayout()
        cores_label = QLabel("Dask Workers:")
        cores_layout.addWidget(cores_label)

        import os
        max_cores = os.cpu_count() or 4
        default_cores = max(1, int(max_cores * 0.75))  # 75% of available cores

        self.cores_spinbox = QSpinBox()
        self.cores_spinbox.setMinimum(1)
        self.cores_spinbox.setMaximum(max_cores)
        self.cores_spinbox.setValue(default_cores)
        self.cores_spinbox.setToolTip(f"Number of Dask workers (1-{max_cores}). Default: {default_cores} (75% of available cores)")
        cores_layout.addWidget(self.cores_spinbox)

        cores_layout.addWidget(QLabel(f"/ {max_cores} cores"))
        cores_layout.addStretch()
        left_layout.addLayout(cores_layout)

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
            item = QListWidgetItem(recipe_name)  # Removed emoji - using native checkbox instead
            item.setData(Qt.UserRole, recipe_file)  # Store full path
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)  # Enable checkbox
            item.setCheckState(Qt.Unchecked)  # Initially unchecked
            self.recipe_list.addItem(item)
            self.recipe_items[recipe_name] = item

        self.log_viewer.append(f"Loaded {len(recipe_files)} recipes from {recipe_dir}")

    def select_all_recipes(self):
        """Check all recipes in the list."""
        for i in range(self.recipe_list.count()):
            self.recipe_list.item(i).setCheckState(Qt.Checked)

    def select_no_recipes(self):
        """Uncheck all recipes in the list."""
        for i in range(self.recipe_list.count()):
            self.recipe_list.item(i).setCheckState(Qt.Unchecked)

    def start_processing(self):
        """Start batch processing of selected recipes."""
        print("DEBUG: start_processing() called")

        # Get checked recipes (using checkboxes instead of selection)
        selected_items = []
        for i in range(self.recipe_list.count()):
            item = self.recipe_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_items.append(item)

        print(f"DEBUG: Found {len(selected_items)} selected recipes")

        if not selected_items:
            QMessageBox.warning(
                self,
                "No Recipes Selected",
                "Please check at least one recipe to process."
            )
            return

        if not self.workspace_path:
            QMessageBox.warning(
                self,
                "No Workspace",
                "Please select a workspace directory first."
            )
            return

        print(f"DEBUG: Workspace validated: {self.workspace_path}")

        # Get recipe file paths
        recipe_files = [item.data(Qt.UserRole) for item in selected_items]

        # Update UI state
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(recipe_files))
        self.status_label.setText(f"Processing 0 of {len(recipe_files)}...")
        self.log_viewer.clear()

        print("DEBUG: UI state updated")

        # Conditionally create and show terminal popup if checkbox is checked
        show_terminal = self.show_terminal_checkbox.isChecked()
        if show_terminal:
            self.log_popup = LogPopupDialog(self)
            self.log_popup.clear_log()
            self.log_popup.show()
        else:
            self.log_popup = None  # No popup if not requested

        # Mark all selected as "Queued"
        for item in selected_items:
            recipe_name = os.path.basename(item.data(Qt.UserRole))
            item.setText(recipe_name)  # No emoji needed - using checkboxes
            item.setForeground(QColor("gray"))

        # Start processing thread with optional output capture
        move_recipes = self.move_recipes_checkbox.isChecked()
        n_workers = self.cores_spinbox.value()

        print(f"DEBUG: Creating thread with n_workers={n_workers}, capture_output={show_terminal}")

        self.processor_thread = BatchProcessorThread(
            recipe_files,
            self.workspace_path,
            move_recipes,
            capture_output=show_terminal,  # Capture stdout/stderr if terminal is shown
            n_workers=n_workers  # Number of Dask workers from spinner
        )

        print("DEBUG: Thread object created")

        self.processor_thread.progress_update.connect(self.on_progress_update)
        self.processor_thread.log_message.connect(self.on_log_message)
        self.processor_thread.terminal_output.connect(self.on_terminal_output)
        self.processor_thread.processing_complete.connect(self.on_processing_complete)

        print("DEBUG: Signals connected")
        print("DEBUG: Calling thread.start()")

        self.processor_thread.start()

        print("DEBUG: thread.start() returned")

    def stop_processing(self):
        """Stop batch processing."""
        if self.processor_thread and self.processor_thread.isRunning():
            self.processor_thread.stop()
            self.processor_thread.wait()  # Wait for thread to finish
            self.log_viewer.append("\n[Batch processing stopped]")

            # Reset UI state completely
            self.run_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.progress_bar.setValue(0)
            self.status_label.setText("Ready")
            self.processor_thread = None

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
        Handle high-level log message from processing thread.
        Shows only in main GUI log viewer.

        Args:
            message: Log message string
        """
        # Update integrated log viewer ONLY
        self.log_viewer.append(message)

        # Auto-scroll to bottom
        scrollbar = self.log_viewer.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @pyqtSlot(str)
    def on_terminal_output(self, message):
        """
        Handle raw terminal output (stdout/stderr) from processing thread.
        Shows only in terminal popup window.

        Args:
            message: Raw output message string
        """
        # Only route to popup if it exists (terminal checkbox was checked)
        if self.log_popup:
            self.log_popup.append_log(message)

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
