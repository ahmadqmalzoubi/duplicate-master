# Duplicate File Finder 🔍

A high-performance, parallel Python tool to detect and manage duplicate files — with flexible hashing, logging, reporting, and safe deletion options.

---

## ⚡ Features

- ✅ **Parallel hashing** for large-scale scanning (6x+ faster)
- 🎯 **Accuracy modes**: Full, Quick (4KB), Multi-region
- 📁 **Recursive scan** with symlink/hidden file filtering
- 🧾 **Export results** to JSON/CSV
- 🧼 **Safe deletion** with dry-run, force, and **interactive file-level selection**
- 📦 **Saving space analysis** included in report
- 📜 **Verbose logging** with optional file log

---

## 📦 Installation

```bash
git clone https://github.com/ahmadqmalzoubi/file-duplicate-finder.git
cd file-duplicate-finder
pip install -r requirements.txt
```

---

## 🚀 Usage

### Command-Line Interface (CLI)

To get started, you can run a scan on a directory using the following command:
```bash
python3 -m filedupfinder.cli ~/data
```

Here are some common examples:

- **Fast mode (first 4KB only):**
  ```bash
  python3 -m filedupfinder.cli ~/data --quick
  ```

- **High-accuracy mode (first/middle/last 4KB):**
  ```bash
  python3 -m filedupfinder.cli ~/data --multi-region
  ```

- **Scan with custom file size limits (5 MB to 500 MB):**
  ```bash
  python3 -m filedupfinder.cli ~/data --minsize 5 --maxsize 500
  ```

- **Export results:**
  ```bash
  python3 -m filedupfinder.cli ~/data --json-out duplicates.json --csv-out duplicates.csv
  ```

- **Simulate deletion (dry-run):**
  ```bash
  python3 -m filedupfinder.cli ~/data --delete --dry-run
  ```

- **Interactive deletion per group with file selection:**
  ```bash
  python3 -m filedupfinder.cli ~/data --delete --interactive
  ```

### Graphical User Interface (GUI)

This tool also includes a graphical interface built with PySide6. To run it, you first need to install the GUI dependencies:

```bash
pip install -r requirements.txt
```

Then, you can launch the GUI with the following command:
```bash
python3 -m gui.gui_app
```
Alternatively, if you installed the package, you can use the entry point:
```bash
filedupfinder-gui
```
The GUI provides an intuitive way to:
- Select a folder to scan.
- View duplicate files in a sortable table.
- Filter results by path and file size.
- Delete selected files safely.
- Export results to JSON or CSV.

### Command Line Interface

```bash
# Basic scan
filedupfinder /path/to/scan

# Scan with size limits (in MB)
filedupfinder --minsize 5 --maxsize 500 /path/to/scan

# Quick scan (faster, less accurate)
filedupfinder --quick /path/to/scan

# Exclude certain file types and directories
filedupfinder --exclude "*.tmp,*.bak" --exclude-dir ".git,node_modules" /path/to/scan

# Dry run deletion (see what would be deleted)
filedupfinder --delete --dry-run /path/to/scan

# Actually delete duplicates (keep one copy)
filedupfinder --delete /path/to/scan

# Export results to JSON
filedupfinder --json-out results.json /path/to/scan

# Export results to CSV
filedupfinder --csv-out results.csv /path/to/scan

# Run demo mode (creates test files, scans, shows results, cleans up)
filedupfinder --demo
```

### Graphical User Interface

1. **Launch the GUI:**
   ```bash
   python -m gui.gui_app
   ```

2. **Using the GUI:**
   - Click "Select Folder" to choose a directory to scan
   - Configure scan options (file size limits, exclusions, scan mode)
   - Click "Start Scan" to begin the duplicate detection
   - Use the "🎬 Run Demo" button to see a demonstration with test files
   - Review results in the table and log output
   - Export results to JSON or CSV if needed
   - Enable deletion options to remove duplicates

3. **Demo Mode:**
   - Click the "🎬 Run Demo" button to run a demonstration
   - The demo creates temporary test files with known duplicates
   - Scans the test files and shows results
   - Automatically cleans up when finished
   - Perfect for testing the tool's functionality

---

## 🛠️ Command-Line Options

| Flag              | Description                                                       | Default |
|-------------------|-------------------------------------------------------------------|---------|
| `path`            | The base directory to start scanning from.                        | (Required) |
| `--quick`         | Fast but less accurate (hash first 4KB)                           | `False` |
| `--multi-region`  | Hash 3 parts (start/middle/end) for accuracy                      | `False` |
| `--minsize`       | Minimum file size to consider (MB)                                | `4 MB`  |
| `--maxsize`       | Maximum file size to consider (MB)                                | `4096 MB` (4 GB) |
| `--threads`       | Number of hashing threads                                          | Auto    |
| `--logfile`       | Path to save log output                                            | None    |
| `--loglevel`      | Set logging verbosity (debug/info/warning/...)                    | `info`  |
| `--json-out`      | Save results as JSON                                               | None    |
| `--csv-out`       | Save results as CSV                                                | None    |
| `--delete`        | Enable duplicate deletion                                          | `False` |
| `--dry-run`       | Simulate deletion without removing files                           | `True`  |
| `--force`         | Skip deletion confirmation                                         | `False` |
| `--interactive`   | Prompt before deleting each group; choose files by number          | `False` |
| `--exclude`       | Glob pattern to exclude files (e.g. `*.bak`, `Thumbs.db`)          | None    |
| `--exclude-dir`   | Directory names to exclude (e.g. `.git`, `node_modules`)           | None    |
| `--exclude-hidden`| Exclude hidden files and directories (starting with dot)           | `False` |

---

## 📊 Performance Tips

- **SSDs / NVMe**: Use `--threads 16` or more
- **Network storage**: Use `--threads 4-8`
- **Fast scan**: `--quick` + high threads
- **Accurate scan**: `--multi-region` + dry-run

---

## 💡 How It Works

1. **Phase 1**: Group files by size  
2. **Phase 2**: Hash files in parallel (configurable mode)  
3. **Phase 3**: (If needed) Verify groups using full hashing  
4. **Phase 4**: Report or delete duplicates

```mermaid
graph TD
    A[Scan Files] --> B[Hash First N Bytes]
    B --> C{Duplicate Candidates?}
    C -->|Yes| D[Full Hash Verify]
    C -->|No| E[Skip]
    D --> F[Report/Export/Delete]
```

---

## ✋ Interactive Deletion Mode

When using `--delete --interactive`, you will be prompted for each duplicate group.

You can:

- Type `a` to delete **all but the first** file (safe default)
- Enter a list of file numbers to delete specific ones (e.g. `1,2,3`)
- Type `s` to **skip** the group

Example prompt:
```
📂 Duplicate group (Size: 2.1 MB, Hash: 91ac5e2a):
  [0] /home/user/docs/file1.pdf
  [1] /home/user/Downloads/file1 (copy).pdf
  [2] /mnt/backup/file1 (1).pdf
Enter number(s) of files to delete (comma-separated), 'a' for all but first, or 's' to skip:
```

---

## 🔐 Safety-First Deletion

- Only extra copies in each duplicate group are deleted
- Default mode is dry-run (`--dry-run`)
- Use `--interactive` for manual review
- Use `--force` for automatic cleanup

---

## 🤝 Contributing

1. Create a feature branch:
   ```bash
   git checkout -b feat/my-feature
   ```
2. Follow PEP 8 conventions
3. Write tests for new features
4. Run the test suite:
   ```bash
   python -m pytest tests/
   ```
5. Ensure all tests pass before submitting a pull request

---

## 🧪 Testing

This project includes a comprehensive unit test suite with **54 tests** covering all core functionality.

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run tests with verbose output
python -m pytest tests/ -v

# Run tests for a specific module
python -m pytest tests/test_analyzer.py -v

# Run tests with coverage (if pytest-cov is installed)
python -m pytest tests/ --cov=filedupfinder
```

### Test Coverage

The test suite covers all core modules:

- **analyzer.py** (11 tests) - Space analysis and byte formatting
- **cli.py** (6 tests) - Command-line argument parsing and validation
- **deduper.py** (7 tests) - Duplicate detection logic (quick/full mode)
- **deletion.py** (10 tests) - File deletion and interactive handling
- **exporter.py** (7 tests) - JSON/CSV export functionality
- **hasher.py** (3 tests) - File hashing and batch processing
- **logger.py** (6 tests) - Logging setup and configuration
- **scanner.py** (4 tests) - File discovery and filtering

### Test Features

- **Mock-based testing** - No filesystem dependencies for fast execution
- **Edge case coverage** - Empty data, errors, invalid inputs
- **Interactive mode testing** - User input simulation
- **Error handling** - File deletion failures, parsing errors
- **Fast execution** - All tests run in under 0.1 seconds

### Development Workflow

1. Write tests for new features
2. Run the test suite: `python -m pytest tests/`
3. Ensure all tests pass before committing
4. Add new test files to the `tests/` directory

---

## 📜 License

This project is licensed under the **GNU General Public License v3.0**.

See the [LICENSE](LICENSE) file for details.