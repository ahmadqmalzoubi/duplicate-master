import os
import sys
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Union, Optional, Callable
import logging
from tqdm import tqdm

DEFAULT_THREADS = min(32, (os.cpu_count() or 1) + 4)
logger = logging.getLogger(__name__)


def blake2bsum(filename: str, buffer_size: Union[int, str], multi_region: bool) -> str:
    """
    Computes the BLAKE2b hash of a file.

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
    file_size = os.path.getsize(filename)

    # Determine the actual buffer size
    actual_buffer_size: Optional[int]
    if buffer_size == "auto":
        actual_buffer_size = -1 if file_size <= 8192 else 4096
    elif isinstance(buffer_size, int):
        actual_buffer_size = buffer_size
    else:
        raise TypeError("buffer_size must be an int or 'auto'")

    with open(filename, 'rb') as f:
        if multi_region and actual_buffer_size != -1 and file_size > 12288:
            for pos in [0, file_size // 2 - 2048, max(0, file_size - 4096)]:
                f.seek(pos)
                h.update(f.read(4096))
        else:
            if actual_buffer_size == -1:
                while chunk := f.read(8192):  # Read in chunks for large files
                    h.update(chunk)
            else:
                h.update(f.read(actual_buffer_size))
    return h.hexdigest()


def batch_hash_files(
    paths: List[str],
    buffer_size: Union[int, str],
    multi_region: bool,
    threads: int,
    progress_callback: Optional[Callable[[int], None]] = None
) -> Dict[str, str]:
    """
    Hashes a batch of files in parallel.

    Args:
        paths: A list of file paths to hash.
        buffer_size: The buffer size to use for hashing.
        multi_region: Whether to use multi-region hashing.
        threads: The number of threads to use.
        progress_callback: An optional callback to report progress percentage.

    Returns:
        A dictionary mapping file paths to their hashes.
    """
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(
            blake2bsum, p, buffer_size, multi_region): p for p in paths}
        results = {}
        last_percent = -1

        with tqdm(total=len(futures), desc="Hashing files", disable=(sys.stdout is None or progress_callback is not None)) as pbar:
            for i, future in enumerate(as_completed(futures)):
                path = futures[future]
                try:
                    results[path] = future.result()
                except (OSError, Exception) as e:
                    logger.error(f"Could not process {path}: {e}")
                finally:
                    pbar.update(1)
                    if progress_callback:
                        percent = int(((i + 1) / len(futures)) * 100)
                        if percent > last_percent:
                            progress_callback(percent)
                            last_percent = percent
        return results
