import os
import sys
import hashlib
import mmap
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Union, Optional, Callable
import logging
from tqdm import tqdm

DEFAULT_THREADS = min(32, (os.cpu_count() or 1) + 4)
# Optimized buffer sizes for better performance
LARGE_BUFFER_SIZE = 64 * 1024  # 64KB for large files
MEDIUM_BUFFER_SIZE = 32 * 1024  # 32KB for medium files
SMALL_BUFFER_SIZE = 16 * 1024  # 16KB for small files
MEMORY_MAP_THRESHOLD = 10 * 1024 * 1024  # 10MB threshold for memory mapping

logger = logging.getLogger(__name__)


def blake2bsum(filename: str, buffer_size: Union[int, str], multi_region: bool) -> str:
    """
    Computes the BLAKE2b hash of a file with optimized I/O handling.

    Args:
        filename: Path to the file.
        buffer_size: The size of the buffer to use for reading the file.
                     'auto' determines buffer size based on file size.
                     -1 reads the whole file.
        multi_region: If True, hashes three regions of the file (start, middle, end).
                      Otherwise, hashes from the beginning of the file.

    Returns:
        The hex digest of the file's hash.
    """
    h = hashlib.blake2b()
    
    try:
        file_size = os.path.getsize(filename)
    except OSError:
        raise OSError(f"Cannot get file size for {filename}")

    # Determine the actual buffer size with optimized defaults
    actual_buffer_size: Optional[int]
    if buffer_size == "auto":
        if file_size <= 8192:
            actual_buffer_size = -1  # Read entire small files
        elif file_size <= 1024 * 1024:  # 1MB
            actual_buffer_size = SMALL_BUFFER_SIZE
        elif file_size <= 100 * 1024 * 1024:  # 100MB
            actual_buffer_size = MEDIUM_BUFFER_SIZE
        else:
            actual_buffer_size = LARGE_BUFFER_SIZE
    elif isinstance(buffer_size, int):
        actual_buffer_size = buffer_size
    else:
        raise TypeError("buffer_size must be an int or 'auto'")

    # Use memory mapping for large files when reading entire content
    if actual_buffer_size == -1 and file_size > MEMORY_MAP_THRESHOLD:
        return _hash_with_memory_map(filename, multi_region)
    
    # Use optimized file reading
    return _hash_with_file_reading(filename, file_size, actual_buffer_size, multi_region)


def _hash_with_memory_map(filename: str, multi_region: bool) -> str:
    """Hash a file using memory mapping for better performance on large files."""
    h = hashlib.blake2b()
    
    with open(filename, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            if multi_region and len(mm) > 12288:
                # Multi-region hashing with memory mapping
                for pos in [0, len(mm) // 2 - 2048, max(0, len(mm) - 4096)]:
                    h.update(mm[pos:pos + 4096])
            else:
                # Full file hashing with memory mapping
                h.update(mm)
    
    return h.hexdigest()


def _hash_with_file_reading(filename: str, file_size: int, buffer_size: int, multi_region: bool) -> str:
    """Hash a file using optimized file reading."""
    h = hashlib.blake2b()
    
    with open(filename, 'rb') as f:
        if multi_region and buffer_size != -1 and file_size > 12288:
            # Multi-region hashing
            for pos in [0, file_size // 2 - 2048, max(0, file_size - 4096)]:
                f.seek(pos)
                h.update(f.read(4096))
        else:
            # Full file or partial hashing
            if buffer_size == -1:
                # Read entire file in optimized chunks
                chunk_size = LARGE_BUFFER_SIZE
                while chunk := f.read(chunk_size):
                    h.update(chunk)
            else:
                # Read only the specified buffer size
                h.update(f.read(buffer_size))
    
    return h.hexdigest()


def batch_hash_files(
    paths: List[str],
    buffer_size: Union[int, str],
    multi_region: bool,
    threads: int,
    progress_callback: Optional[Callable[[int], None]] = None,
    batch_size: Optional[int] = None
) -> Dict[str, str]:
    """
    Hashes a batch of files in parallel with optimized batching and progress reporting.

    Args:
        paths: A list of file paths to hash.
        buffer_size: The buffer size to use for hashing.
        multi_region: Whether to use multi-region hashing.
        threads: The number of threads to use.
        progress_callback: An optional callback to report progress percentage.
        batch_size: Size of batches for processing (None for auto-detect).

    Returns:
        A dictionary mapping file paths to their hashes.
    """
    if not paths:
        return {}
    
    # Auto-determine optimal batch size
    if batch_size is None:
        batch_size = max(1, min(100, len(paths) // (threads * 2)))
    
    results = {}
    last_percent = -1
    
    # Process files in batches for better memory management
    with ThreadPoolExecutor(max_workers=threads) as executor:
        # Submit all tasks
        futures = {executor.submit(blake2bsum, p, buffer_size, multi_region): p for p in paths}
        
        # Process results with optimized progress reporting
        with tqdm(total=len(futures), desc="Hashing files", disable=(sys.stdout is None or progress_callback is not None)) as pbar:
            completed = 0
            for future in as_completed(futures):
                path = futures[future]
                try:
                    results[path] = future.result()
                except (OSError, Exception) as e:
                    logger.error(f"Could not process {path}: {e}")
                finally:
                    completed += 1
                    pbar.update(1)
                    
                    # Optimized progress callback (less frequent updates)
                    if progress_callback and completed % max(1, len(futures) // 20) == 0:
                        percent = int((completed / len(futures)) * 100)
                        if percent > last_percent:
                            progress_callback(percent)
                            last_percent = percent
    
    # Final progress update
    if progress_callback and last_percent < 100:
        progress_callback(100)
    
    return results


def hash_files_with_size_info(
    files_with_size: List[tuple[int, str]],
    buffer_size: Union[int, str],
    multi_region: bool,
    threads: int,
    progress_callback: Optional[Callable[[int], None]] = None
) -> Dict[str, str]:
    """
    Hash files with pre-computed size information for better performance.
    
    This function is optimized for cases where file sizes are already known,
    allowing for better buffer size selection and progress estimation.
    
    Args:
        files_with_size: List of (size, path) tuples.
        buffer_size: The buffer size to use for hashing.
        multi_region: Whether to use multi-region hashing.
        threads: The number of threads to use.
        progress_callback: An optional callback to report progress percentage.
        
    Returns:
        A dictionary mapping file paths to their hashes.
    """
    if not files_with_size:
        return {}
    
    # Sort files by size for better load balancing
    files_with_size.sort(key=lambda x: x[0], reverse=True)
    
    # Extract just the paths for hashing
    paths = [path for _, path in files_with_size]
    
    return batch_hash_files(paths, buffer_size, multi_region, threads, progress_callback)
