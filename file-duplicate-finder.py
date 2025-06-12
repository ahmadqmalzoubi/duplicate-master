#!/usr/bin/env python3

import os
import hashlib
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import logging


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


def get_files_recursively(baseDir):
    """Thread-safe file scanner with hidden/symlink filtering"""
    for dentry in os.scandir(baseDir):
        if dentry.name.startswith('.') or dentry.is_symlink():
            continue
        elif dentry.is_dir(follow_symlinks=False):
            yield from get_files_recursively(dentry.path)
        else:
            yield dentry.path  # Return paths instead of DirEntry for thread safety


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


def find_duplicates(base_dir, min_size, max_size, quick_mode, multi_region):
    """Parallelized duplicate detection"""
    size_groups = defaultdict(list)

    # Phase 1: Scan and group by size (single-threaded)
    print("🔍 Scanning directory structure...")
    files = []
    for path in tqdm(get_files_recursively(base_dir), desc="Indexing files"):
        try:
            file_size = os.path.getsize(path)
            if min_size < file_size < max_size:
                files.append((file_size, path))
        except OSError:
            continue

    # Phase 2: First-pass hashing (parallel)
    print("🔢 First-pass hashing...")
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
        print("✅ Verifying potential duplicates...")
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
    args = parser.parse_args()

    duplicates = find_duplicates(
        os.path.abspath(args.basedir),
        args.minsize,
        args.maxsize,
        args.quick,
        args.multi_region
    )

    # Print results
    print(
        f"\n📝 Duplicate Report ({'Quick' if args.quick else 'Multi-Region' if args.multi_region else 'Full'})")
    total_files = sum(len(g) for g in duplicates.values())
    print(f"Found {len(duplicates)} groups ({total_files} files total)")

    for (size, hash), paths in sorted(duplicates.items()):
        print(f"\n■ Size: {size:,} bytes  Hash: {hash[:8]}...")
        for path in paths:
            print(f"  → {path}")


if __name__ == "__main__":
    main()
