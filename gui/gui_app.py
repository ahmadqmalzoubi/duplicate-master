from filedupfinder.exporter import export_results
from filedupfinder.logger import setup_logger
from filedupfinder.analyzer import analyze_space_savings, format_bytes
from filedupfinder.deduper import find_duplicates
from PySide6.QtGui import QIcon, QFont, QColor, QBrush
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QLabel, QFileDialog, QTableWidget, QTableWidgetItem, QHBoxLayout, QTextEdit,
    QCheckBox, QRadioButton, QButtonGroup, QGroupBox, QMessageBox,
    QLineEdit, QSpinBox
)
import sys
import os
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'src')))


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

    def __init__(self, folder, logger):
        super().__init__()
        self.folder = folder
        self.logger = logger

    def run(self):
        try:
            self.log.emit(f"\n\n🗂️ Scan started for: {self.folder}\n{'-'*60}")
            duplicates = find_duplicates(
                base_dir=self.folder,
                min_size=4096,
                max_size=4294967296,
                quick_mode=True,
                multi_region=False,
                exclude=[],
                exclude_dir=[],
                exclude_hidden=False,
                threads=os.cpu_count(),
                logger=self.logger
            )
            self.log.emit(
                f"✅ Scan complete. Found {len(duplicates)} duplicate groups.")
            self.finished.emit(duplicates)
        except Exception as e:
            self.log.emit(f"❌ Error during scan: {str(e)}")
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
            "Group", "Size", "Hash (last 8)", "Path"])
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setSelectionMode(QTableWidget.MultiSelection)
        self.result_table.setSortingEnabled(True)
        self.result_table.setFont(QFont("Segoe UI", 10))

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter by file path...")
        self.filter_input.textChanged.connect(self.apply_filter)

        self.min_size_input = QSpinBox()
        self.min_size_input.setPrefix("Min KB: ")
        self.min_size_input.setMaximum(1024 * 1024)
        self.min_size_input.setValue(0)
        self.min_size_input.valueChanged.connect(self.apply_filter)

        self.max_size_input = QSpinBox()
        self.max_size_input.setPrefix("Max KB: ")
        self.max_size_input.setMaximum(1024 * 1024)
        self.max_size_input.setValue(1024 * 1024)
        self.max_size_input.valueChanged.connect(self.apply_filter)

        self.select_button = QPushButton(
            QIcon.fromTheme("folder"), "Select Folder")
        self.select_button.clicked.connect(self.select_folder)

        self.scan_button = QPushButton(
            QIcon.fromTheme("system-search"), "Start Scan")
        self.scan_button.clicked.connect(self.start_scan)
        self.scan_button.setEnabled(False)

        self.confirm_delete_button = QPushButton(
            QIcon.fromTheme("edit-delete"), "🗑️ Confirm Deletion")
        self.confirm_delete_button.setVisible(False)
        self.confirm_delete_button.clicked.connect(
            self.confirm_selected_deletion)

        self.export_json_button = QPushButton(
            QIcon.fromTheme("document-save"), "📤 Export to JSON")
        self.export_json_button.clicked.connect(self.export_to_json)
        self.export_json_button.setVisible(False)

        self.export_csv_button = QPushButton(
            QIcon.fromTheme("document-save"), "📤 Export to CSV")
        self.export_csv_button.clicked.connect(self.export_to_csv)
        self.export_csv_button.setVisible(False)

        self.delete_checkbox = QCheckBox("Enable deletion")
        self.dry_run_radio = QRadioButton("Dry run only")
        self.dry_run_radio.setChecked(True)
        self.delete_all_radio = QRadioButton(
            "Delete all duplicates (keep one)")
        self.interactive_radio = QRadioButton("Prompt before each group")

        self.delete_mode_group = QButtonGroup()
        self.delete_mode_group.addButton(self.dry_run_radio)
        self.delete_mode_group.addButton(self.delete_all_radio)
        self.delete_mode_group.addButton(self.interactive_radio)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        filter_layout.addWidget(self.filter_input)
        filter_layout.addWidget(self.min_size_input)
        filter_layout.addWidget(self.max_size_input)

        deletion_layout = QVBoxLayout()
        deletion_layout.addWidget(self.delete_checkbox)
        deletion_layout.addWidget(self.dry_run_radio)
        deletion_layout.addWidget(self.delete_all_radio)
        deletion_layout.addWidget(self.interactive_radio)

        deletion_group = QGroupBox("Deletion Options")
        deletion_group.setLayout(deletion_layout)

        filter_group = QGroupBox("Results Filter")
        filter_group.setLayout(filter_layout)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.scan_button)
        button_layout.addWidget(self.confirm_delete_button)
        button_layout.addWidget(self.export_json_button)
        button_layout.addWidget(self.export_csv_button)

        layout = QVBoxLayout()
        layout.addWidget(self.folder_label)
        layout.addLayout(button_layout)
        layout.addWidget(deletion_group)
        layout.addWidget(filter_group)
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
        # self.logger.addHandler(self._log_handler())

        self.selected_folder = None
        self.duplicates = {}
        self.thread = None

    def _log_handler(self):
        from logging import Handler, Formatter

        class QtHandler(Handler):
            def emit(inner_self, record):
                msg = inner_self.format(record)
                self.logger_output.append(msg)

        handler = QtHandler()
        handler.setFormatter(Formatter('%(message)s'))
        return handler

        return QtHandler()

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
        self.confirm_delete_button.setVisible(False)
        self.export_json_button.setVisible(False)
        self.export_csv_button.setVisible(False)

        if not self.selected_folder:
            return

        self.thread = QThread()
        self.worker = ScanWorker(self.selected_folder, self.logger)
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.log.connect(self.logger_output.append)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def on_scan_finished(self, duplicates):
        self.thread.quit()
        self.thread.wait()
        self.worker.deleteLater()
        self.thread.deleteLater()

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

        if self.delete_checkbox.isChecked():
            if self.interactive_radio.isChecked():
                self.confirm_delete_button.setVisible(True)
            else:
                self.perform_deletion()

        self.export_json_button.setVisible(True)
        self.export_csv_button.setVisible(True)

    def apply_filter(self):
        keyword = self.filter_input.text().lower()
        min_kb = self.min_size_input.value()
        max_kb = self.max_size_input.value()

        for row in range(self.result_table.rowCount()):
            path = self.result_table.item(row, 3).text().lower()
            size_bytes = int(self.result_table.item(row, 3).toolTip())
            size_kb = size_bytes / 1024

            matches_keyword = keyword in path
            matches_size = min_kb <= size_kb <= max_kb

            self.result_table.setRowHidden(
                row, not (matches_keyword and matches_size))

    def perform_deletion(self):
        self.logger.info("\n🚮 Deletion Process Started")
        dry_run = self.dry_run_radio.isChecked()

        for (size, hash), paths in sorted(self.duplicates.items()):
            if len(paths) < 2:
                continue
            to_delete = paths[1:]

            for path in to_delete:
                if dry_run:
                    self.logger.info(f"[DRY-RUN] Would delete: {path}")
                else:
                    try:
                        os.remove(path)
                        self.logger.info(f"Deleted: {path}")
                    except Exception as e:
                        self.logger.error(f"❌ Failed to delete {path}: {e}")

        if dry_run:
            self.logger.info("\n✅ Dry-run complete. No files were deleted.")
        else:
            self.logger.info("\n✅ Deletion complete.")

    def confirm_selected_deletion(self):
        selected_rows = self.result_table.selectionModel().selectedRows()
        if not selected_rows:
            self.logger.info("⚠️ No files selected for deletion.")
            return

        confirm = QMessageBox.question(self, "Confirm Deletion",
                                       f"Are you sure you want to delete {len(selected_rows)} selected file(s)?",
                                       QMessageBox.Yes | QMessageBox.No)

        if confirm != QMessageBox.Yes:
            self.logger.info("⏹️ Deletion cancelled by user.")
            return

        deleted_count = 0
        for row in selected_rows:
            path_item = self.result_table.item(row.row(), 3)
            if path_item:
                path = path_item.text()
                try:
                    os.remove(path)
                    self.logger.info(f"🗑️ Deleted: {path}")
                    deleted_count += 1
                except Exception as e:
                    self.logger.error(f"❌ Failed to delete {path}: {e}")

        self.logger.info(
            f"\n✅ Deletion complete. {deleted_count} files deleted.")

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
        if not self.duplicates:
            self.logger.info("⚠️ No results to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV", "duplicates.csv", "CSV Files (*.csv)")
        if path:
            try:
                export_results(self.duplicates, type(
                    'Args', (), {"json_out": None, "csv_out": path}), self.logger)
            except Exception as e:
                self.logger.error(f"❌ Failed to export CSV: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
