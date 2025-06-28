import os
from collections import defaultdict
from typing import Optional, Callable, Dict, Any, List, Tuple
from .scanner import get_files_recursively, get_files_with_size_filter
from .hasher import batch_hash_files, hash_files_with_size_info


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
    progress_callback: Optional[Callable[[int, str], None]] = None,
    use_optimized_scanning: bool = True
) -> Dict[Tuple[int, str], List[str]]:
    """
    Find duplicate files in a directory with optimized performance.

    Args:
        base_dir: Base directory to scan.
        min_size: Minimum file size in bytes.
        max_size: Maximum file size in bytes.
        quick_mode: Use quick scan mode.
        multi_region: Use multi-region hashing.
        exclude: File patterns to exclude.
        exclude_dir: Directory names to exclude.
        exclude_hidden: Exclude hidden files.
        threads: Number of threads to use.
        logger: Logger instance.
        progress_callback: Progress callback function.
        use_optimized_scanning: Use optimized scanning with early size filtering.

    Returns:
        Dictionary mapping (size, hash) tuples to lists of file paths.
    """
    if progress_callback:
        progress_callback(0, "Scanning for files...")

    # Use optimized scanning with early size filtering
    if use_optimized_scanning:
        files_with_size = list(get_files_with_size_filter(
            base_dir, exclude, exclude_dir, exclude_hidden, 
            min_size, max_size, logger, max_workers=threads
        ))
        
        if progress_callback:
            progress_callback(15, f"Found {len(files_with_size)} files to process...")
    else:
        # Fallback to original scanning method
        files = []
        for path in get_files_recursively(base_dir, exclude, exclude_dir, exclude_hidden, logger, max_workers=threads):
            try:
                size = os.path.getsize(path)
                if min_size < size < max_size:
                    files.append((size, path))
            except OSError:
                continue
        files_with_size = files
        
        if progress_callback:
            progress_callback(15, f"Found {len(files_with_size)} files to process...")

    if not files_with_size:
        if progress_callback:
            progress_callback(100, "No files found matching criteria.")
        return {}

    def quick_scan_progress(p: int):
        if progress_callback:
            # Scale this phase to be 15% -> 65% of total
            progress_callback(15 + int(p * 0.5), f"Hashing... ({p}%)")

    # Use optimized hashing with size information
    if use_optimized_scanning:
        hash_results = hash_files_with_size_info(
            files_with_size,
            4096 if quick_mode else "auto",
            multi_region and not quick_mode,
            threads,
            progress_callback=quick_scan_progress if progress_callback else None
        )
    else:
        # Fallback to original hashing method
        hash_results = batch_hash_files(
            [p for _, p in files_with_size],
            4096 if quick_mode else "auto",
            multi_region and not quick_mode,
            threads,
            progress_callback=quick_scan_progress if progress_callback else None
        )

    # Group files by size and hash
    size_hash_groups = defaultdict(list)
    for size, path in files_with_size:
        if path in hash_results:
            size_hash_groups[(size, hash_results[path])].append(path)

    if not quick_mode:
        if progress_callback:
            progress_callback(65, "Verifying full file hashes...")

        def full_scan_progress(p: int):
            if progress_callback:
                # Scale this phase to be 65% -> 95% of total
                progress_callback(65 + int(p * 0.3), f"Verifying... ({p}%)")

        # Get files that need full verification
        verify_map = {p: (s, size_hash_groups[(s, h)]) for (
            s, h), paths in size_hash_groups.items() for p in paths if len(paths) > 1}
        
        if not verify_map:  # No potential duplicates found
            if progress_callback:
                progress_callback(100, "Scan complete. No duplicates found.")
            return {}

        # Use optimized hashing for verification
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
