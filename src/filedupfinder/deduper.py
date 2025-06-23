import os
from collections import defaultdict
from typing import Optional, Callable, Dict, Any, List, Tuple
from .scanner import get_files_recursively
from .hasher import batch_hash_files


def find_duplicates(
    base_dir: str,
    min_size: int,
    max_size: int,
    quick_mode: bool,
    multi_region: bool,
    exclude: List[str],
    exclude_dir: List[str],
    exclude_hidden: bool,
    threads: int,
    logger: Any,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[Tuple[int, str], List[str]]:

    if progress_callback:
        progress_callback(0, "Scanning for files...")

    files = []
    for path in get_files_recursively(base_dir, exclude, exclude_dir, exclude_hidden, logger):
        try:
            size = os.path.getsize(path)
            if min_size < size < max_size:
                files.append((size, path))
        except OSError:
            continue
    
    if progress_callback:
        progress_callback(15, "Hashing files (Quick Scan)...")

    def quick_scan_progress(p: int):
        if progress_callback:
            # Scale this phase to be 15% -> 65% of total
            progress_callback(15 + int(p * 0.5), f"Hashing... ({p}%)")

    size_hash_groups = defaultdict(list)
    hash_results = batch_hash_files(
        [p for _, p in files],
        4096 if quick_mode else "auto",
        multi_region and not quick_mode,
        threads,
        progress_callback=quick_scan_progress if progress_callback else None
    )

    for size, path in files:
        if path in hash_results:
            size_hash_groups[(size, hash_results[path])].append(path)

    if not quick_mode:
        if progress_callback:
            progress_callback(65, "Verifying full file hashes...")

        def full_scan_progress(p: int):
            if progress_callback:
                # Scale this phase to be 65% -> 95% of total
                progress_callback(65 + int(p * 0.3), f"Verifying... ({p}%)")

        verify_map = {p: (s, size_hash_groups[(s, h)]) for (
            s, h), paths in size_hash_groups.items() for p in paths if len(paths) > 1}
        
        if not verify_map: # No potential duplicates found
            if progress_callback:
                progress_callback(100, "Scan complete. No duplicates found.")
            return {}

        verify_results = batch_hash_files(
            list(verify_map.keys()),
            -1,
            False,
            threads,
            progress_callback=full_scan_progress if progress_callback else None
        )

        duplicates = defaultdict(list)
        for path, hash_val in verify_results.items():
            size, _ = verify_map[path]
            duplicates[(size, hash_val)].append(path)

        if progress_callback:
            progress_callback(100, "Scan complete.")
        return {k: v for k, v in duplicates.items() if len(v) > 1}
    else:
        if progress_callback:
            progress_callback(100, "Scan complete.")
        return {k: v for k, v in size_hash_groups.items() if len(v) > 1}
