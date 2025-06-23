import os
import fnmatch
from typing import List, Iterator, Any


def get_files_recursively(
    base_dir: str,
    exclude: List[str],
    exclude_dir: List[str],
    exclude_hidden: bool,
    logger: Any
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

    Yields:
        str: Path to each file that passes all exclusion filters.

    Examples:
        >>> for file_path in get_files_recursively('/home/user', ['*.tmp'], ['.git'], True, logger):
        ...     print(file_path)
        /home/user/document.txt
        /home/user/image.jpg
    """
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
                    yield from get_files_recursively(path, exclude, exclude_dir, exclude_hidden, logger)
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
