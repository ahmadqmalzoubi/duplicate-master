from .cli import parse_args
from .logger import setup_logger
from .deduper import find_duplicates
from .analyzer import analyze_space_savings, format_bytes
from .deletion import handle_deletion
from .exporter import export_results
import os


def main() -> None:
    """
    Main entry point for the duplicate file finder application.

    This function orchestrates the entire duplicate file finding process:
    1. Parses command-line arguments
    2. Sets up logging
    3. Validates the target directory
    4. Performs the duplicate file scan
    5. Analyzes and reports results
    6. Handles deletion if requested
    7. Exports results if specified

    The function provides comprehensive feedback to the user including:
    - Scan progress and status
    - Summary statistics (groups, files, space usage)
    - Error handling and logging
    - Export functionality

    Examples:
        >>> main()
        # Scans current directory and reports results

    Command-line usage:
        $ filedupfinder /path/to/scan
        $ filedupfinder --delete --dry-run /path/to/scan
        $ filedupfinder --minsize 5 --maxsize 500 /path/to/scan

    Note:
        - Exits with error code 1 if the target directory is invalid
        - Provides detailed logging for debugging
        - Supports both scan-only and deletion modes
        - Handles export to JSON/CSV formats
    """
    args = parse_args()
    logger = setup_logger(args)

    if not os.path.exists(args.basedir) or not os.path.isdir(args.basedir):
        logger.error(f"Invalid directory: {args.basedir}")
        return

    duplicates = find_duplicates(
        base_dir=os.path.abspath(args.basedir),
        min_size=args.minsize,
        max_size=args.maxsize,
        quick_mode=args.quick,
        multi_region=args.multi_region,
        exclude=args.exclude,
        exclude_dir=args.exclude_dir,
        exclude_hidden=args.exclude_hidden,
        threads=args.threads,
        logger=logger
    )

    total_space, savings = analyze_space_savings(duplicates)
    num_groups = len(duplicates)
    num_files = sum(len(paths) for paths in duplicates.values())

    logger.info("\n📊 Scan Summary:")
    logger.info(f"   • {num_groups} duplicate groups detected")
    logger.info(f"   • {num_files} duplicate files in total")
    logger.info(
        f"   • {format_bytes(total_space)} of space used by duplicates")
    logger.info(f"   • {format_bytes(savings)} can be reclaimed")

    if num_groups == 0:
        logger.info("   • No duplicate files found in the scanned directory.")

    if args.delete:
        handle_deletion(duplicates, args, logger)

    export_results(duplicates, args, logger)


if __name__ == "__main__":
    main()
