import os
import fnmatch


def get_files_recursively(base_dir, exclude, exclude_dir, exclude_hidden, logger):
    for entry in os.scandir(base_dir):
        if entry.is_symlink():
            logger.debug(f"Skipping symlink: {entry.path}")
            continue
        if exclude_hidden and entry.name.startswith('.'):
            continue
        if entry.is_dir(follow_symlinks=False):
            if entry.name in exclude_dir:
                continue
            yield from get_files_recursively(entry.path, exclude, exclude_dir, exclude_hidden, logger)
        else:
            if any(fnmatch.fnmatch(entry.name, pattern) for pattern in exclude):
                continue
            yield entry.path
