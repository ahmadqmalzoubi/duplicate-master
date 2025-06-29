from duplicatemaster.exporter import export_results
from duplicatemaster.logger import setup_logger
from duplicatemaster.analyzer import analyze_space_savings, format_bytes
from duplicatemaster.deduper import find_duplicates
from duplicatemaster.deletion import delete_files
from PySide6.QtGui import QIcon, QFont, QColor, QBrush
from PySide6.QtCore import Qt, QThread, Signal, QObject, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QLabel, QFileDialog, QTableWidget, QTableWidgetItem, QHBoxLayout, QTextEdit,
    QCheckBox, QRadioButton, QButtonGroup, QGroupBox, QMessageBox,
    QLineEdit, QSpinBox, QAbstractItemView, QProgressBar
)
import sys
import os
from typing import Dict, List, Tuple, Any, Optional, Union


class SortableItem(QTableWidgetItem):
    def __init__(self, display_text, sort_value):
        super().__init__(display_text)
        self.sort_value = sort_value

    def __lt__(self, other):
        if isinstance(other, SortableItem):
            return self.sort_value < other.sort_value
        return super().__lt__(other)


class ScanWorker(QObject):
    finished = Signal(object)
    log = Signal(str)
    progress = Signal(int, str)

    def __init__(self, folder, options):
        super().__init__()
        self.folder = folder
        self.options = options

    def run(self):
        class SignallingLogger:
            def __init__(self, log_signal):
                self.log_signal = log_signal

            def info(self, msg):
                self.log_signal.emit(msg)

            def debug(self, msg):
                pass  # Or emit a different signal if needed

            def warning(self, msg):
                self.log_signal.emit(f"WARNING: {msg}")

            def error(self, msg):
                self.log_signal.emit(f"ERROR: {msg}")

        logger_proxy = SignallingLogger(self.log)

        def log_msg(msg):
            logger_proxy.info(msg)

        try:
            log_msg(f"\n\n🗂️ Scan started for: {self.folder}\n{'-'*60}")
            duplicates = find_duplicates(
                base_dir=self.folder,
                min_size=self.options['min_size'],
                max_size=self.options['max_size'],
                quick_mode=self.options['quick_mode'],
                multi_region=self.options['multi_region'],
                exclude=self.options['exclude_files'],
                exclude_dir=self.options['exclude_dirs'],
                exclude_hidden=self.options['exclude_hidden'],
                threads=os.cpu_count() or 1,
                logger=logger_proxy,
                progress_callback=self.progress.emit
            )
            log_msg(
                f"✅ Scan complete. Found {len(duplicates)} duplicate groups.")
            self.finished.emit(duplicates)
        except Exception as e:
            log_msg(f"❌ Error during scan: {str(e)}")
            self.finished.emit({})


class DemoWorker(QObject):
    finished = Signal(object)
    log = Signal(str)
    progress = Signal(int, str)

    def __init__(self):
        super().__init__()

    def run(self):
        from duplicatemaster.demo import run_demo
        from duplicatemaster.deduper import find_duplicates
        from duplicatemaster.analyzer import analyze_space_savings, format_bytes
        import tempfile
        from pathlib import Path

        class SignallingLogger:
            def __init__(self, log_signal):
                self.log_signal = log_signal

            def info(self, msg):
                self.log_signal.emit(msg)

            def debug(self, msg):
                pass

            def warning(self, msg):
                self.log_signal.emit(f"WARNING: {msg}")

            def error(self, msg):
                self.log_signal.emit(f"ERROR: {msg}")

        logger_proxy = SignallingLogger(self.log)

        try:
            logger_proxy.info("🎬 Starting File Duplicate Finder Demo")
            logger_proxy.info("=" * 50)

            # Create temporary directory for demo
            with tempfile.TemporaryDirectory() as temp_dir:
                base_dir = Path(temp_dir) / "demo_files"
                base_dir.mkdir()

                # Create demo files
                logger_proxy.info("📁 Creating demo files with duplicates...")
                from duplicatemaster.demo import create_demo_files
                file_mapping = create_demo_files(base_dir)

                # Run scan
                logger_proxy.info("🔍 Starting demo scan...")
                duplicates = find_duplicates(
                    base_dir=str(base_dir),
                    min_size=0,
                    max_size=1024 * 1024 * 1024,  # 1GB max
                    quick_mode=True,
                    multi_region=False,
                    exclude=[],
                    exclude_dir=[],
                    exclude_hidden=False,
                    threads=4,
                    logger=logger_proxy,
                    progress_callback=self.progress.emit
                )

                # Show results
                total_space, savings = analyze_space_savings(duplicates)
                num_groups = len(duplicates)
                num_files = sum(len(paths) for paths in duplicates.values())

                logger_proxy.info("\n" + "="*60)
                logger_proxy.info("🎯 DEMO RESULTS")
                logger_proxy.info("="*60)
                logger_proxy.info(f"📊 Found {num_groups} duplicate groups")
                logger_proxy.info(f"📁 Total duplicate files: {num_files}")
                logger_proxy.info(f"💾 Space used by duplicates: {format_bytes(total_space)}")
                logger_proxy.info(f"🗑️  Space that can be reclaimed: {format_bytes(savings)}")
                logger_proxy.info("="*60)

                if num_groups > 0:
                    logger_proxy.info("\n📋 Duplicate Groups Found:")
                    logger_proxy.info("-" * 40)

                    for i, ((size, hash_val), paths) in enumerate(duplicates.items(), 1):
                        logger_proxy.info(f"\n🔍 Group {i} (Size: {format_bytes(size)}, Hash: {hash_val[:8]}...)")
                        for j, path in enumerate(paths):
                            rel_path = os.path.relpath(path)
                            logger_proxy.info(f"  [{j}] {rel_path}")

                logger_proxy.info("\n✅ Demo completed successfully!")
                logger_proxy.info("💡 This demonstrates how the tool identifies and groups duplicate files.")

                self.finished.emit(duplicates)

        except Exception as e:
            logger_proxy.error(f"❌ Demo failed: {str(e)}")
            self.finished.emit({})


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Duplicate File Finder")
        self.resize(1000, 600)

        self.logger_output = QTextEdit()
        self.logger_output.setReadOnly(True)

        self.folder_label = QLabel("No folder selected")
        self.result_table = QTableWidget(0, 4)
        self.result_table.setHorizontalHeaderLabels([
            "Group", "Size", "Hash", "Path"])
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.result_table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.result_table.setSortingEnabled(True)
        # self.result_table.setFont(QFont("Sans Serif", 10))

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter by file path...")
        self.filter_input.textChanged.connect(self.apply_filter)

        self.min_size_input = QSpinBox()
        self.min_size_input.setPrefix("Min MB: ")
        self.min_size_input.setMaximum(10240)  # 10 GB
        self.min_size_input.setValue(1) # 1 MB

        self.max_size_input = QSpinBox()
        self.max_size_input.setPrefix("Max MB: ")
        self.max_size_input.setMaximum(1024 * 20)  # 20 GB
        self.max_size_input.setValue(4096)  # 4 GB

        # --- Scan Options ---
        self.quick_scan_radio = QRadioButton("Quick Scan (fast, less accurate)")
        self.quick_scan_radio.setToolTip("Hashes only the first 4KB of each file. Fast but may have false positives.")
        self.full_scan_radio = QRadioButton("Full Scan (accurate, default)")
        self.full_scan_radio.setToolTip("Hashes the entire file content. Most accurate but slower for large files.")
        self.full_scan_radio.setChecked(True)
        self.multi_region_scan_radio = QRadioButton("Multi-region Scan (balanced)")
        self.multi_region_scan_radio.setToolTip("Hashes three regions (start, middle, end) of each file. Good balance of speed and accuracy.")

        self.scan_mode_group = QButtonGroup()
        self.scan_mode_group.addButton(self.quick_scan_radio)
        self.scan_mode_group.addButton(self.full_scan_radio)
        self.scan_mode_group.addButton(self.multi_region_scan_radio)

        self.exclude_files_input = QLineEdit()
        self.exclude_files_input.setPlaceholderText("e.g., *.tmp, *.bak")
        self.exclude_files_input.setToolTip("Comma-separated glob patterns to exclude files (e.g., *.tmp, *.bak, Thumbs.db)")
        self.exclude_dirs_input = QLineEdit()
        self.exclude_dirs_input.setPlaceholderText("e.g., .git, node_modules, $RECYCLE.BIN")
        self.exclude_dirs_input.setText(".git, node_modules, $RECYCLE.BIN, System Volume Information, Windows")
        self.exclude_dirs_input.setToolTip("Comma-separated directory names to exclude from scanning")
        self.exclude_hidden_checkbox = QCheckBox("Exclude hidden files and folders")
        self.exclude_hidden_checkbox.setToolTip("Skip files and folders that start with a dot (.)")
        self.exclude_hidden_checkbox.setChecked(True)

        scan_options_layout = QVBoxLayout()
        scan_options_layout.addWidget(QLabel("Scan Mode:"))
        scan_options_layout.addWidget(self.quick_scan_radio)
        scan_options_layout.addWidget(self.full_scan_radio)
        scan_options_layout.addWidget(self.multi_region_scan_radio)
        
        size_filter_layout = QHBoxLayout()
        size_filter_layout.addWidget(QLabel("File Size (MB):"))
        size_filter_layout.addWidget(self.min_size_input)
        size_filter_layout.addWidget(self.max_size_input)
        scan_options_layout.addLayout(size_filter_layout)

        scan_options_layout.addSpacing(10)
        scan_options_layout.addWidget(QLabel("Exclude Files (comma-separated globs):"))
        scan_options_layout.addWidget(self.exclude_files_input)
        scan_options_layout.addWidget(QLabel("Exclude Directories (comma-separated):"))
        scan_options_layout.addWidget(self.exclude_dirs_input)
        scan_options_layout.addWidget(self.exclude_hidden_checkbox)

        self.scan_options_group = QGroupBox("Scan Options")
        self.scan_options_group.setLayout(scan_options_layout)

        # --- Deletion Options ---
        deletion_layout = QVBoxLayout()
        self.delete_checkbox = QCheckBox("Enable deletion")
        self.delete_checkbox.setToolTip("Enable the deletion functionality. When unchecked, only scanning is performed.")
        deletion_layout.addWidget(self.delete_checkbox)
        self.dry_run_radio = QRadioButton("Dry run only")
        self.dry_run_radio.setToolTip("Simulate deletion without actually removing files. Shows what would be deleted.")
        self.dry_run_radio.setChecked(True)
        self.delete_all_radio = QRadioButton("Delete all duplicates (keep one)")
        self.delete_all_radio.setToolTip("Automatically delete all duplicate files, keeping one copy from each group.")
        self.interactive_radio = QRadioButton("Prompt before each group")
        self.interactive_radio.setToolTip("Manually select which files to delete from each duplicate group.")

        self.delete_mode_group = QButtonGroup()
        self.delete_mode_group.addButton(self.dry_run_radio)
        self.delete_mode_group.addButton(self.delete_all_radio)
        self.delete_mode_group.addButton(self.interactive_radio)

        deletion_layout.addWidget(self.dry_run_radio)
        deletion_layout.addWidget(self.delete_all_radio)
        deletion_layout.addWidget(self.interactive_radio)

        self.deletion_group = QGroupBox("Deletion Options")
        self.deletion_group.setLayout(deletion_layout)

        # --- Filter ---
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter Results:"))
        filter_layout.addWidget(self.filter_input)
        
        self.filter_group = QGroupBox("Results Filter")
        self.filter_group.setLayout(filter_layout)
        self.filter_group.setToolTip("Filter the displayed results by file path. Does not affect the scan itself.")

        button_layout = QHBoxLayout()
        self.select_button = QPushButton(
            QIcon.fromTheme("folder"), "Select Folder")
        self.select_button.clicked.connect(self.select_folder)

        self.demo_button = QPushButton(
            QIcon.fromTheme("media-playback-start"), "🎬 Run Demo")
        self.demo_button.setToolTip("Run a demo with test files to see how the tool works")
        self.demo_button.clicked.connect(self.run_demo)

        self.scan_button = QPushButton(
            QIcon.fromTheme("system-search"), "Start Scan")
        self.scan_button.clicked.connect(self.start_scan)
        self.scan_button.setEnabled(False)

        self.delete_button = QPushButton(
            QIcon.fromTheme("edit-delete"), "🗑️ Delete Duplicates...")
        self.delete_button.setVisible(False)
        self.delete_button.clicked.connect(self.run_deletion_process)

        self.export_json_button = QPushButton(
            QIcon.fromTheme("document-save"), "📤 Export to JSON")
        self.export_json_button.clicked.connect(self.export_to_json)
        self.export_json_button.setVisible(False)

        self.export_csv_button = QPushButton(
            QIcon.fromTheme("document-save"), "📤 Export to CSV")
        self.export_csv_button.clicked.connect(self.export_to_csv)
        self.export_csv_button.setVisible(False)

        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.demo_button)
        button_layout.addWidget(self.scan_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.export_json_button)
        button_layout.addWidget(self.export_csv_button)

        layout = QVBoxLayout()
        layout.addWidget(self.folder_label)
        layout.addLayout(button_layout)
        layout.addWidget(self.deletion_group)
        layout.addWidget(self.scan_options_group)
        layout.addWidget(self.filter_group)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.result_table)
        layout.addWidget(QLabel("Log Output:"))
        layout.addWidget(self.logger_output)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        import logging
        self.logger = logging.getLogger("fdf_gui")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            self.logger.addHandler(self._log_handler())
        self.logger.propagate = False

        self.selected_folder: Optional[str] = None
        self.duplicates: Dict[Tuple[int, str], List[str]] = {}
        self.thread: Optional[QThread] = None
        self.worker: Optional[Union[ScanWorker, DemoWorker]] = None

    def _log_handler(self):
        from logging import Handler, Formatter

        class QtHandler(Handler):
            def emit(inner_self, record):
                msg = inner_self.format(record)
                self.logger_output.append(msg)

        handler = QtHandler()
        handler.setFormatter(Formatter('%(message)s'))
        return handler

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder to Scan")
        if folder:
            self.selected_folder = folder
            self.folder_label.setText(folder)
            self.scan_button.setEnabled(True)

    def start_scan(self):
        self.logger_output.clear()
        self.result_table.setRowCount(0)
        self.delete_button.setVisible(False)
        self.export_json_button.setVisible(False)
        self.export_csv_button.setVisible(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Starting scan...")
        self.set_controls_enabled(False)

        if not self.selected_folder:
            self.set_controls_enabled(True)
            return

        scan_options = {
            "min_size": self.min_size_input.value() * 1024 * 1024,  # MB to Bytes
            "max_size": self.max_size_input.value() * 1024 * 1024,  # MB to Bytes
            "quick_mode": self.quick_scan_radio.isChecked(),
            "multi_region": self.multi_region_scan_radio.isChecked(),
            "exclude_files": [p.strip() for p in self.exclude_files_input.text().split(',') if p.strip()],
            "exclude_dirs": [d.strip() for d in self.exclude_dirs_input.text().split(',') if d.strip()],
            "exclude_hidden": self.exclude_hidden_checkbox.isChecked(),
        }

        self.thread = QThread()
        self.worker = ScanWorker(self.selected_folder, scan_options)
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.log.connect(self.logger_output.append)
        self.worker.progress.connect(self.update_progress)
        self.thread.started.connect(
            lambda: QTimer.singleShot(100, self.start_worker_run))
        self.thread.start()

    def start_worker_run(self):
        if self.worker:
            self.worker.run()

    def on_scan_finished(self, duplicates: Dict[Tuple[int, str], List[str]]):
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        
        if self.worker:
            self.worker.deleteLater()
        
        if self.thread:
            self.thread.deleteLater()

        self.worker = None
        self.thread = None

        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.set_controls_enabled(True)

        self.duplicates = duplicates

        total_space, savings = analyze_space_savings(self.duplicates)

        self.result_table.setSortingEnabled(False)
        group_id = 1
        for (size, hash), paths in sorted(self.duplicates.items()):
            for path in paths:
                row = self.result_table.rowCount()
                self.result_table.insertRow(row)
                self.result_table.setItem(
                    row, 0, SortableItem(str(group_id), group_id))
                self.result_table.setItem(
                    row, 1, SortableItem(format_bytes(size), size))
                item = QTableWidgetItem(f"{hash[:8]}...{hash[-8:]}")
                item.setToolTip(hash)
                self.result_table.setItem(row, 2, item)
                path_item = QTableWidgetItem(path)
                path_item.setToolTip(str(size))
                self.result_table.setItem(row, 3, path_item)
            group_id += 1

        self.result_table.setSortingEnabled(True)

        self.logger.info("")
        self.logger.info("📊 Scan Summary:")
        self.logger.info(
            f"   • {len(self.duplicates)} duplicate groups detected")
        self.logger.info(
            f"   • {sum(len(v) for v in self.duplicates.values())} duplicate files in total")
        self.logger.info(
            f"   • {format_bytes(total_space)} of space used by duplicates")
        self.logger.info(f"   • {format_bytes(savings)} can be reclaimed")

        if not self.duplicates:
            self.logger.info("   • No duplicate files found in the scanned directory.")

        self.delete_button.setVisible(
            bool(self.duplicates) and self.delete_checkbox.isChecked())
        self.export_json_button.setVisible(bool(self.duplicates))
        self.export_csv_button.setVisible(bool(self.duplicates))

    def set_controls_enabled(self, enabled: bool):
        self.select_button.setEnabled(enabled)
        self.scan_button.setEnabled(enabled)
        self.filter_group.setEnabled(enabled)
        self.deletion_group.setEnabled(enabled)
        self.scan_options_group.setEnabled(enabled)
        # Also control the delete/export buttons
        if enabled:
            self.delete_button.setVisible(
                bool(self.duplicates) and self.delete_checkbox.isChecked())
            self.export_json_button.setVisible(bool(self.duplicates))
            self.export_csv_button.setVisible(bool(self.duplicates))
        else:
            self.delete_button.setVisible(False)
            self.export_json_button.setVisible(False)
            self.export_csv_button.setVisible(False)

    def update_progress(self, value: int, message: str):
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)

    def apply_filter(self):
        keyword = self.filter_input.text().lower()

        for row in range(self.result_table.rowCount()):
            path_item = self.result_table.item(row, 3)
            size_item = self.result_table.item(row, 3)
            if not path_item or not size_item:
                continue

            path = path_item.text().lower()

            matches_keyword = keyword in path

            self.result_table.setRowHidden(
                row, not matches_keyword)

    def run_deletion_process(self):
        if self.interactive_radio.isChecked():
            self.confirm_selected_deletion()
        else:  # Covers "Delete all" and "Dry run"
            if not self.dry_run_radio.isChecked():
                confirm = QMessageBox.question(self, "Confirm Deletion",
                                               f"Are you sure you want to delete all duplicate files, keeping one from each group?",
                                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if confirm != QMessageBox.StandardButton.Yes:
                    self.logger.info("⏹️ Deletion cancelled by user.")
                    return
            self.perform_deletion()

    def perform_deletion(self):
        self.logger.info("\n🚮 Deletion Process Started")
        dry_run = self.dry_run_radio.isChecked()

        files_to_delete = []
        for (size, hash), paths in sorted(self.duplicates.items()):
            if len(paths) < 2:
                continue
            files_to_delete.extend(paths[1:])

        if files_to_delete:
            delete_files(files_to_delete, dry_run, self.logger)

        if dry_run:
            self.logger.info("\n✅ Dry-run complete. No files were deleted.")
        else:
            self.logger.info("\n✅ Deletion complete.")
            # Consider re-scanning or removing deleted rows from table
        # self.start_scan() # Removed to prevent re-scan loop

    def confirm_selected_deletion(self):
        selected_rows = self.result_table.selectionModel().selectedRows()
        if not selected_rows:
            self.logger.info("⚠️ No files selected for deletion.")
            return

        confirm = QMessageBox.question(self, "Confirm Deletion",
                                       f"Are you sure you want to delete {len(selected_rows)} selected file(s)?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if confirm != QMessageBox.StandardButton.Yes:
            self.logger.info("⏹️ Deletion cancelled by user.")
            return

        paths_to_delete = []
        for row in selected_rows:
            path_item = self.result_table.item(row.row(), 3)
            if path_item:
                paths_to_delete.append(path_item.text())

        if paths_to_delete:
            # Assuming not a dry-run since it's an interactive deletion
            delete_files(paths_to_delete, dry_run=False, logger_obj=self.logger)
            self.logger.info(
                f"\n✅ Deletion complete. {len(paths_to_delete)} files deleted.")
            # To reflect the changes, we can remove the deleted rows from the table
            # or the user can manually re-scan. For simplicity, we'll let them re-scan.
            # A more advanced implementation could remove the specific rows.

        # Refresh the view
        # self.start_scan() # Removed to prevent re-scan loop

    def export_to_json(self):
        if not self.duplicates:
            self.logger.info("⚠️ No results to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export to JSON", "duplicates.json", "JSON Files (*.json)")
        if path:
            try:
                export_results(self.duplicates, type(
                    'Args', (), {"json_out": path, "csv_out": None}), self.logger)
            except Exception as e:
                self.logger.error(f"❌ Failed to export JSON: {e}")

    def export_to_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV", "", "CSV Files (*.csv)")
        if file_path:
            try:
                export_results(self.duplicates, type('Args', (), {
                    'csv_out': file_path
                })(), self.logger)
                self.logger.info(f"✅ Exported to CSV: {file_path}")
            except Exception as e:
                self.logger.error(f"❌ Export failed: {e}")

    def run_demo(self):
        """Run the demo functionality in a separate thread."""
        self.logger_output.clear()
        self.result_table.setRowCount(0)
        self.delete_button.setVisible(False)
        self.export_json_button.setVisible(False)
        self.export_csv_button.setVisible(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Running demo...")
        self.set_controls_enabled(False)

        # Create a demo worker thread
        self.thread = QThread()
        self.worker = DemoWorker()
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self.on_demo_finished)
        self.worker.log.connect(self.logger_output.append)
        self.worker.progress.connect(self.update_progress)
        self.thread.started.connect(
            lambda: QTimer.singleShot(100, self.start_worker_run))
        self.thread.start()

    def on_demo_finished(self, duplicates: Dict[Tuple[int, str], List[str]]):
        """Handle demo completion."""
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        
        if self.worker:
            self.worker.deleteLater()
        
        if self.thread:
            self.thread.deleteLater()

        self.worker = None
        self.thread = None

        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        # Enable controls but properly handle scan button state
        self.select_button.setEnabled(True)
        self.scan_button.setEnabled(bool(self.selected_folder))  # Only enable if folder selected
        self.filter_group.setEnabled(True)
        self.deletion_group.setEnabled(True)
        self.scan_options_group.setEnabled(True)

        # Show demo results in table
        self.duplicates = duplicates
        total_space, savings = analyze_space_savings(self.duplicates)

        self.result_table.setSortingEnabled(False)
        group_id = 1
        for (size, hash), paths in sorted(self.duplicates.items()):
            for path in paths:
                row = self.result_table.rowCount()
                self.result_table.insertRow(row)
                self.result_table.setItem(
                    row, 0, SortableItem(str(group_id), group_id))
                self.result_table.setItem(
                    row, 1, SortableItem(format_bytes(size), size))
                item = QTableWidgetItem(f"{hash[:8]}...{hash[-8:]}")
                item.setToolTip(hash)
                self.result_table.setItem(row, 2, item)
                path_item = QTableWidgetItem(path)
                path_item.setToolTip(str(size))
                self.result_table.setItem(row, 3, path_item)
            group_id += 1

        self.result_table.setSortingEnabled(True)

        # Show export buttons for demo results
        self.export_json_button.setVisible(bool(self.duplicates))
        self.export_csv_button.setVisible(bool(self.duplicates))


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
