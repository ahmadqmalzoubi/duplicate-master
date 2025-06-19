import os
import fnmatch


def get_files_recursively(base_dir, exclude, exclude_dir, exclude_hidden, logger):
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
