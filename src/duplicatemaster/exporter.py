import json
import csv
from typing import Dict, List, Tuple, Any


def export_results(
    duplicates: Dict[Tuple[int, str], List[str]],
    args: Any,
    logger: Any
) -> None:
    """
    Export duplicate file results to JSON and/or CSV formats.

    This function takes the results of a duplicate file scan and exports them
    to the specified output formats. JSON export creates a structured format
    with all duplicate groups, while CSV export creates a flat list with one
    row per duplicate file.

    Args:
        duplicates: A dictionary mapping (file_size, file_hash) tuples to lists
                   of file paths that are duplicates of each other.
        args: Command-line arguments object containing json_out and csv_out paths.
        logger: Logger instance for recording export progress and errors.

    Examples:
        >>> duplicates = {(1024, 'abc123'): ['/path/file1.txt', '/path/file2.txt']}
        >>> args = type('Args', (), {'json_out': 'results.json', 'csv_out': None})()
        >>> export_results(duplicates, args, logger)
        # Creates results.json with the duplicate data

    Note:
        - JSON format groups duplicates by size and hash
        - CSV format creates one row per duplicate file
        - Both formats include file size, hash, and file paths
    """
    data = [{"size_bytes": size, "hash": hash, "paths": paths}
            for (size, hash), paths in duplicates.items()]

    if args.json_out:
        try:
            with open(args.json_out, 'w') as jf:
                json.dump(data, jf, indent=2)
            logger.info(f"Written to JSON: {args.json_out}")
        except Exception as e:
            logger.error(f"JSON export failed: {e}")

    if args.csv_out:
        try:
            with open(args.csv_out, 'w', newline='') as cf:
                writer = csv.DictWriter(
                    cf, fieldnames=["size_bytes", "hash", "path"])
                writer.writeheader()
                for row in data:
                    for path in row['paths']:
                        writer.writerow(
                            {"size_bytes": row['size_bytes'], "hash": row['hash'], "path": path})
            logger.info(f"Written to CSV: {args.csv_out}")
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
