import argparse
from typing import Any
from .hasher import DEFAULT_THREADS


def parse_args() -> Any:
    """
    Parse command-line arguments for the duplicate file finder application.

    This function sets up the argument parser with all available options for the CLI,
    including scan parameters, output formats, deletion options, and logging settings.
    The function also handles unit conversion from MB to bytes for file size limits.

    Returns:
        argparse.Namespace: Parsed command-line arguments with the following attributes:
            - basedir: Directory to scan (default: current directory)
            - minsize: Minimum file size in MB (default: 4 MB)
            - maxsize: Maximum file size in MB (default: 4096 MB = 4 GB)
            - quick: Enable quick scan mode (default: False)
            - multi_region: Enable multi-region scan mode (default: False)
            - threads: Number of hashing threads (default: auto-detect)
            - loglevel: Logging level (default: info)
            - logfile: Path to log file (default: None)
            - json_out: Path for JSON export (default: None)
            - csv_out: Path for CSV export (default: None)
            - delete: Enable deletion mode (default: False)
            - dry_run: Enable dry-run mode (default: False)
            - force: Skip confirmation prompts (default: False)
            - interactive: Enable interactive deletion (default: False)
            - exclude: List of file patterns to exclude
            - exclude_dir: List of directory names to exclude
            - exclude_hidden: Exclude hidden files (default: False)
            - demo: Run demo mode with test files (creates temporary files, scans, shows results, cleans up)
            - benchmark: Run performance benchmark comparing optimized vs legacy scanning
            - legacy_scan: Use legacy scanning method (disable optimizations)

    Examples:
        >>> args = parse_args()
        >>> print(f"Scanning directory: {args.basedir}")
        >>> print(f"File size range: {args.minsize} - {args.maxsize} MB")
        Scanning directory: .
        File size range: 4 - 4096 MB

    Note:
        - File size arguments (minsize, maxsize) are converted from MB to bytes internally
        - The function handles both required and optional arguments
        - Default values are optimized for typical usage scenarios
    """
    parser = argparse.ArgumentParser(
        description="Parallel duplicate file finder")
    parser.add_argument('basedir', nargs='?', default=".",
                        help='Directory to scan')
    parser.add_argument('--minsize', type=int, default=4,
                        help='Minimum file size in MB (default: 4 MB)')
    parser.add_argument('--maxsize', type=int, default=4096,
                        help='Maximum file size in MB (default: 4096 MB = 4 GB)')
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--multi-region', action='store_true')
    parser.add_argument('--threads', type=int, default=DEFAULT_THREADS)
    parser.add_argument('--loglevel', default="info",
                        choices=["debug", "info", "warning", "error"])
    parser.add_argument('--logfile', type=str)
    parser.add_argument('--json-out', type=str)
    parser.add_argument('--csv-out', type=str)
    parser.add_argument('--delete', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--interactive', action='store_true')
    parser.add_argument('--exclude', action='append', default=[])
    parser.add_argument('--exclude-dir', action='append', default=[])
    parser.add_argument('--exclude-hidden', action='store_true')
    parser.add_argument('--demo', action='store_true', 
                        help='Run demo mode with test files (creates temporary files, scans, shows results, cleans up)')
    parser.add_argument('--benchmark', action='store_true',
                        help='Run performance benchmark comparing optimized vs legacy scanning')
    parser.add_argument('--legacy-scan', action='store_true',
                        help='Use legacy scanning method (disable optimizations)')
    
    args = parser.parse_args()
    
    # Convert MB to bytes for backward compatibility
    args.minsize = args.minsize * 1024 * 1024
    args.maxsize = args.maxsize * 1024 * 1024
    
    return args
