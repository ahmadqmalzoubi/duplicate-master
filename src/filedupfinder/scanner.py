import os
import fnmatch
from typing import List, Iterator, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import threading


def get_files_recursively(
    base_dir: str,
    exclude: List[str],
    exclude_dir: List[str],
    exclude_hidden: bool,
    logger: Any,
    max_workers: Optional[int] = None
) -> Iterator[str]:
    """
    Recursively scan a directory and yield file paths that match the criteria.

    This function walks through a directory tree and yields the paths of all files
    that are not excluded by the specified filters. It handles symlinks, hidden files,
    and provides detailed logging for debugging purposes.

    Args:
        base_dir: The root directory to start scanning from.
        exclude: List of glob patterns to exclude files (e.g., ['*.tmp', '*.bak']).
        exclude_dir: List of directory names to exclude from scanning.
        exclude_hidden: If True, skip files and directories that start with '.'.
        logger: Logger instance for recording scan progress and errors.
        max_workers: Number of threads for parallel scanning (None for auto-detect).

    Yields:
        str: Path to each file that passes all exclusion filters.

    Examples:
        >>> for file_path in get_files_recursively('/home/user', ['*.tmp'], ['.git'], True, logger):
        ...     print(file_path)
        /home/user/document.txt
        /home/user/image.jpg
    """
    if max_workers is None:
        max_workers = min(32, (os.cpu_count() or 1) + 4)
    
    # Use parallel scanning for better performance
    if max_workers > 1:
        yield from _get_files_parallel(base_dir, exclude, exclude_dir, exclude_hidden, logger, max_workers)
    else:
        yield from _get_files_sequential(base_dir, exclude, exclude_dir, exclude_hidden, logger)


def _get_files_sequential(
    base_dir: str,
    exclude: List[str],
    exclude_dir: List[str],
    exclude_hidden: bool,
    logger: Any
) -> Iterator[str]:
    """Sequential file discovery (original implementation)."""
    try:
        if not os.path.isdir(base_dir):
            logger.warning(f"Skipping non-directory path: {base_dir}")
            return

        try:
            entries = list(os.scandir(base_dir))
        except Exception as e:
            logger.warning(f"Cannot scan directory: {base_dir} ({e})")
            return

        for entry in entries:
            try:
                path = entry.path
                if entry.is_symlink():
                    logger.debug(f"Skipping symlink: {path}")
                    continue
                if exclude_hidden and entry.name.startswith('.'):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if entry.name in exclude_dir:
                        logger.debug(f"Excluded directory: {path}")
                        continue
                    yield from _get_files_sequential(path, exclude, exclude_dir, exclude_hidden, logger)
                else:
                    if any(fnmatch.fnmatch(entry.name, pattern) for pattern in exclude):
                        logger.debug(f"Excluded file: {path}")
                        continue
                    logger.debug(f"Found file: {path}")
                    yield path
            except Exception as e:
                logger.warning(f"Skipping entry (inner): {entry} ({e})")
    except Exception as e:
        logger.warning(f"Top-level error scanning {base_dir}: {e}")


def _get_files_parallel(
    base_dir: str,
    exclude: List[str],
    exclude_dir: List[str],
    exclude_hidden: bool,
    logger: Any,
    max_workers: int
) -> Iterator[str]:
    """Parallel file discovery using multiple threads."""
    discovered_files = set()
    lock = threading.Lock()
    
    def scan_directory(dir_path: str) -> List[str]:
        """Scan a single directory and return file paths."""
        files = []
        try:
            if not os.path.isdir(dir_path):
                return files

            try:
                entries = list(os.scandir(dir_path))
            except Exception as e:
                logger.warning(f"Cannot scan directory: {dir_path} ({e})")
                return files

            subdirs = []
            for entry in entries:
                try:
                    path = entry.path
                    if entry.is_symlink():
                        logger.debug(f"Skipping symlink: {path}")
                        continue
                    if exclude_hidden and entry.name.startswith('.'):
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name in exclude_dir:
                            logger.debug(f"Excluded directory: {path}")
                            continue
                        subdirs.append(path)
                    else:
                        if any(fnmatch.fnmatch(entry.name, pattern) for pattern in exclude):
                            logger.debug(f"Excluded file: {path}")
                            continue
                        logger.debug(f"Found file: {path}")
                        files.append(path)
                except Exception as e:
                    logger.warning(f"Skipping entry: {entry} ({e})")
            
            # Recursively scan subdirectories
            if subdirs:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_dir = {executor.submit(scan_directory, subdir): subdir for subdir in subdirs}
                    for future in as_completed(future_to_dir):
                        try:
                            files.extend(future.result())
                        except Exception as e:
                            logger.warning(f"Error scanning subdirectory: {e}")
                            
        except Exception as e:
            logger.warning(f"Error scanning directory {dir_path}: {e}")
        
        return files
    
    # Start parallel scanning
    all_files = scan_directory(base_dir)
    
    # Yield files while avoiding duplicates
    for file_path in all_files:
        with lock:
            if file_path not in discovered_files:
                discovered_files.add(file_path)
                yield file_path


def get_files_with_size_filter(
    base_dir: str,
    exclude: List[str],
    exclude_dir: List[str],
    exclude_hidden: bool,
    min_size: int,
    max_size: int,
    logger: Any,
    max_workers: Optional[int] = None
) -> Iterator[tuple[int, str]]:
    """
    Recursively scan a directory and yield (size, path) tuples with early size filtering.
    
    This optimized version filters files by size during the discovery phase,
    reducing the number of files that need to be processed in later stages.
    
    Args:
        base_dir: The root directory to start scanning from.
        exclude: List of glob patterns to exclude files.
        exclude_dir: List of directory names to exclude from scanning.
        exclude_hidden: If True, skip files and directories that start with '.'.
        min_size: Minimum file size in bytes.
        max_size: Maximum file size in bytes.
        logger: Logger instance for recording scan progress and errors.
        max_workers: Number of threads for parallel scanning.
        
    Yields:
        tuple[int, str]: (file_size, file_path) for files that pass all filters.
    """
    if max_workers is None:
        max_workers = min(32, (os.cpu_count() or 1) + 4)
    
    def scan_with_size_filter(dir_path: str) -> List[tuple[int, str]]:
        """Scan a single directory and return (size, path) tuples."""
        files = []
        try:
            if not os.path.isdir(dir_path):
                return files

            try:
                entries = list(os.scandir(dir_path))
            except Exception as e:
                logger.warning(f"Cannot scan directory: {dir_path} ({e})")
                return files

            subdirs = []
            for entry in entries:
                try:
                    path = entry.path
                    if entry.is_symlink():
                        logger.debug(f"Skipping symlink: {path}")
                        continue
                    if exclude_hidden and entry.name.startswith('.'):
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name in exclude_dir:
                            logger.debug(f"Excluded directory: {path}")
                            continue
                        subdirs.append(path)
                    else:
                        if any(fnmatch.fnmatch(entry.name, pattern) for pattern in exclude):
                            logger.debug(f"Excluded file: {path}")
                            continue
                        
                        # Early size filtering
                        try:
                            size = entry.stat().st_size
                            if min_size <= size <= max_size:
                                logger.debug(f"Found file: {path} ({size} bytes)")
                                files.append((size, path))
                        except OSError:
                            logger.debug(f"Cannot get size for: {path}")
                            continue
                            
                except Exception as e:
                    logger.warning(f"Skipping entry: {entry} ({e})")
            
            # Recursively scan subdirectories
            if subdirs:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_dir = {executor.submit(scan_with_size_filter, subdir): subdir for subdir in subdirs}
                    for future in as_completed(future_to_dir):
                        try:
                            files.extend(future.result())
                        except Exception as e:
                            logger.warning(f"Error scanning subdirectory: {e}")
                            
        except Exception as e:
            logger.warning(f"Error scanning directory {dir_path}: {e}")
        
        return files
    
    # Start parallel scanning with size filtering
    all_files = scan_with_size_filter(base_dir)
    
    # Yield files (already filtered by size)
    for size, file_path in all_files:
        yield (size, file_path)
