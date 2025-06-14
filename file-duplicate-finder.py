#!/usr/bin/env python3

import os
import hashlib
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import logging
import json
import csv
import fnmatch


# Set up a logger
logger = logging.getLogger("duplicate_finder")
logger.setLevel(logging.INFO)  # Default level; will be overridden by CLI

# StreamHandler for console output
console_handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Constants
DEFAULT_THREADS = min(32, (os.cpu_count() or 1) + 4)  # Optimal thread count


def get_files_recursively(baseDir, exclude=None, exclude_dir=None, exclude_hidden=False):
    exclude = exclude or []
    exclude_dir = exclude_dir or []
    """Thread-safe file scanner with optional hidden/symlink filtering"""
    for dentry in os.scandir(baseDir):
        if dentry.is_symlink():
            logger.debug(f"Skipping symlink: {dentry.path}")
            continue

        if exclude_hidden and dentry.name.startswith('.'):
            logger.debug(f"Skipping hidden: {dentry.path}")
            continue

        if dentry.is_dir(follow_symlinks=False):
            if dentry.name in exclude_dir:
                logger.debug(f"Skipping excluded directory: {dentry.path}")
                continue
            yield from get_files_recursively(dentry.path, exclude, exclude_dir, exclude_hidden)
        else:
            if any(fnmatch.fnmatch(dentry.name, pattern) for pattern in exclude):
                logger.debug(f"Skipping excluded file: {dentry.path}")
                continue
            yield dentry.path


def blake2bsum(filename, buffer_size="auto", multi_region=False):
    """Thread-safe hashing with three modes"""
    h = hashlib.blake2b()
    file_size = os.path.getsize(filename)

    # Auto-select strategy
    if buffer_size == "auto":
        buffer_size = -1 if file_size <= 8192 else 4096

    with open(filename, 'rb') as f:
        if multi_region and buffer_size != -1 and file_size > 12288:
            regions = [0, file_size // 2 - 2048, max(0, file_size - 4096)]
            for pos in regions:
                f.seek(pos)
                h.update(f.read(4096))
        else:
            if buffer_size == -1:
                while chunk := f.read(8192):
                    h.update(chunk)
            else:
                h.update(f.read(buffer_size))
    return h.hexdigest()


def batch_hash_files(file_paths, buffer_size, multi_region):
    """Process a batch of files in parallel"""
    with ThreadPoolExecutor(max_workers=DEFAULT_THREADS) as executor:
        futures = {
            executor.submit(
                blake2bsum,
                path,
                buffer_size,
                multi_region
            ): path for path in file_paths
        }
        results = {}
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Hashing files",
            unit="file"
        ):
            path = futures[future]
            try:
                results[path] = future.result()
            except (OSError, PermissionError):
                continue
        return results


def find_duplicates(base_dir, min_size, max_size, quick_mode, multi_region, exclude, exclude_dir, exclude_hidden):
    """Parallelized duplicate detection"""

    # Phase 1: Scan and group by size (single-threaded)
    logger.info("🔍 Scanning directory structure...")
    files = []
    for path in tqdm(get_files_recursively(base_dir, exclude, exclude_dir, exclude_hidden), desc="Indexing files"):
        try:
            file_size = os.path.getsize(path)
            if min_size < file_size < max_size:
                files.append((file_size, path))
        except OSError:
            continue

    # Phase 2: First-pass hashing (parallel)
    logger.info("🔢 First-pass hashing...")
    size_hash_groups = defaultdict(list)
    hash_results = batch_hash_files(
        [p for (s, p) in files],
        buffer_size=4096 if quick_mode else "auto",
        multi_region=(multi_region and not quick_mode)
    )

    for file_size, path in files:
        if path in hash_results:
            size_hash_groups[(file_size, hash_results[path])].append(path)

    # Phase 3: Verification (parallel if needed)
    duplicates = defaultdict(list)
    if not quick_mode:
        logger.info("✅ Verifying potential duplicates...")
        verify_files = []
        verify_map = {}  # {hash: original_paths}

        for (size, hash), paths in size_hash_groups.items():
            if len(paths) > 1:
                for path in paths:
                    verify_files.append(path)
                    verify_map[path] = (size, paths)

        verify_results = batch_hash_files(verify_files, -1, False)

        for path, hash in verify_results.items():
            size, original_paths = verify_map[path]
            duplicates[(size, hash)].append(path)

        # Filter single-file groups
        duplicates = {k: v for k, v in duplicates.items() if len(v) > 1}
    else:
        duplicates = {k: v for k, v in size_hash_groups.items() if len(v) > 1}

    return duplicates


def analyze_space_savings(duplicates):
    total_space = 0
    savings = 0
    for (size, _), paths in duplicates.items():
        total_space += size * len(paths)
        savings += size * (len(paths) - 1)
    return total_space, savings


def format_bytes(size):
    for unit in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def main():
    parser = argparse.ArgumentParser(
        description='Parallel duplicate file finder with configurable accuracy')
    parser.add_argument('basedir', nargs='?', default=".",
                        help='directory to search')
    parser.add_argument('--minsize', type=int, default=4096,
                        help='minimum file size in bytes')
    parser.add_argument('--maxsize', type=int, default=4294967296,
                        help='maximum file size in bytes')
    parser.add_argument('--quick', action='store_true',
                        help='fast mode (first 4KB only)')
    parser.add_argument('--multi-region', action='store_true',
                        help='hash first/middle/last 4KB')
    parser.add_argument('--threads', type=int, default=DEFAULT_THREADS,
                        help=f'thread count (default: {DEFAULT_THREADS})')
    parser.add_argument('--loglevel', default="info", choices=["debug", "info", "warning", "error"],
                        help='Set logging verbosity (default: info)')
    parser.add_argument('--logfile', type=str,
                        help='Optional log file path to save output (in addition to console)')
    parser.add_argument('--json-out', type=str,
                        help='Optional path to save duplicate results as JSON')
    parser.add_argument('--csv-out', type=str,
                        help='Optional path to save duplicate results as CSV')
    parser.add_argument('--delete', action='store_true',
                        help='Delete duplicate files (default: false)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simulate deletion without removing any files (default: true)')
    parser.add_argument('--force', action='store_true',
                        help='Skip confirmation before deletion')
    parser.add_argument('--interactive', action='store_true',
                        help='Prompt before deleting each group (used with --delete)')
    parser.add_argument('--exclude', action='append', default=[],
                        help='Glob pattern to exclude files (e.g. *.bak, Thumbs.db)')
    parser.add_argument('--exclude-dir', action='append', default=[],
                        help='Directory names to exclude (e.g. .git, node_modules)')
    parser.add_argument('--exclude-hidden', action='store_true',
                        help='Exclude hidden files and directories (those starting with a dot)')

    args = parser.parse_args()

    # Validate base directory
    if not os.path.exists(args.basedir):
        logger.error(f"❌ The directory '{args.basedir}' does not exist.")
        return
    if not os.path.isdir(args.basedir):
        logger.error(f"❌ The path '{args.basedir}' is not a directory.")
        return

    # Set log level from CLI
    logger.setLevel(getattr(logging, args.loglevel.upper()))

    # Optional file handler
    if args.logfile:
        file_handler = logging.FileHandler(args.logfile)
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        logger.debug(f"Logging to file: {args.logfile}")

    duplicates = find_duplicates(
        os.path.abspath(args.basedir),
        args.minsize,
        args.maxsize,
        args.quick,
        args.multi_region,
        args.exclude,
        args.exclude_dir,
        args.exclude_hidden
    )

    # Compute total duplicate size and potential savings
    total_space, potential_savings = analyze_space_savings(duplicates)

    # Print results
    logger.info(
        f"\n📝 Duplicate Report ({'Quick' if args.quick else 'Multi-Region' if args.multi_region else 'Full'})")

    total_files = sum(len(g) for g in duplicates.values())
    logger.info(f"Found {len(duplicates)} groups ({total_files} files total)")

    for (size, hash), paths in sorted(duplicates.items()):
        logger.info(f"\n■ Size: {size:,} bytes  Hash: {hash[:8]}...")
        for path in paths:
            logger.info(f"  → {path}")

    logger.info(
        f"📦 Total disk space used by duplicates: {format_bytes(total_space)}")
    logger.info(
        f"💸 Potential savings if removed:        {format_bytes(potential_savings)}")

    # Perform deletion or dry-run
    if args.delete:
        if not args.force:
            confirm = input(
                "\n⚠️  Are you sure you want to delete duplicate files? (y/N): ").strip().lower()
            if confirm != 'y':
                logger.info("🛑 Deletion cancelled by user.")
                return

        logger.info(
            f"\n🚮 Starting {'dry-run ' if args.dry_run else ''}deletion process...")

        delete_count = 0
        skipped_groups = 0
        aborted = False

        for (size, hash), paths in sorted(duplicates.items()):
            if args.interactive:
                print(
                    f"\n📂 Duplicate group (Size: {format_bytes(size)}, Hash: {hash[:8]}):")
                for idx, path in enumerate(paths):
                    print(f"  [{idx}] {path}")

                choice = input(
                    "Enter number(s) of files to delete (comma-separated), 'a' for all but first, or 's' to skip: ").strip().lower()

                if choice == 's':
                    logger.info("⏭️ Skipped deletion for this group.")
                    skipped_groups += 1
                    continue
                elif choice == 'a':
                    selected_to_delete = paths[1:]
                else:
                    try:
                        indices = [int(x.strip()) for x in choice.split(',')]
                        selected_to_delete = [paths[i]
                                              for i in indices if 0 <= i < len(paths)]
                    except Exception:
                        logger.warning(
                            "⚠️ Invalid input, skipping this group.")
                        skipped_groups += 1
                        continue
            else:
                selected_to_delete = paths[1:]

            for path in selected_to_delete:
                if args.dry_run:
                    logger.info(f"[DRY-RUN] Would delete: {path}")
                else:
                    try:
                        os.remove(path)
                        logger.info(f"🗑️ Deleted: {path}")
                        delete_count += 1
                    except Exception as e:
                        logger.error(f"❌ Failed to delete {path}: {e}")

        if aborted:
            logger.info("\n⚠️ Deletion process aborted by user.")
        elif args.dry_run:
            logger.info("\n✅ Dry-run completed. No files were deleted.")
        else:
            logger.info(
                f"\n✅ Deletion complete. {delete_count} files deleted.")

        if skipped_groups > 0:
            logger.info(f"ℹ️ Skipped groups: {skipped_groups}")

    # Group duplicate entries by size and hash
    grouped_export_data = []
    for (size, hash), paths in sorted(duplicates.items()):
        grouped_export_data.append({
            "size_bytes": size,
            "hash": hash,
            "paths": paths
        })

    # Export to JSON
    if args.json_out:
        try:
            with open(args.json_out, 'w', encoding='utf-8') as json_file:
                json.dump(grouped_export_data, json_file, indent=2)
            logger.info(f"📝 Duplicate data written to JSON: {args.json_out}")
        except Exception as e:
            logger.error(f"Failed to write JSON output: {e}")

    # Export to CSV
    if args.csv_out:
        try:
            with open(args.csv_out, 'w', newline='', encoding='utf-8') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=[
                                        "size_bytes", "hash", "path"])
                writer.writeheader()
                for row in grouped_export_data:
                    for path in row["paths"]:
                        writer.writerow({
                            "size_bytes": row["size_bytes"],
                            "hash": row["hash"],
                            "path": path
                        })

            logger.info(f"📝 Duplicate data written to CSV: {args.csv_out}")
        except Exception as e:
            logger.error(f"Failed to write CSV output: {e}")


if __name__ == "__main__":
    main()
