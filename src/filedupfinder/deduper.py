import os
from collections import defaultdict
from .scanner import get_files_recursively
from .hasher import batch_hash_files


def find_duplicates(base_dir, min_size, max_size, quick_mode, multi_region, exclude, exclude_dir, exclude_hidden, threads, logger):
    files = []
    for path in get_files_recursively(base_dir, exclude, exclude_dir, exclude_hidden, logger):
        try:
            size = os.path.getsize(path)
            if min_size < size < max_size:
                files.append((size, path))
        except OSError:
            continue

    size_hash_groups = defaultdict(list)
    hash_results = batch_hash_files(
        [p for _, p in files], 4096 if quick_mode else "auto", multi_region and not quick_mode, threads)

    for size, path in files:
        if path in hash_results:
            size_hash_groups[(size, hash_results[path])].append(path)

    if not quick_mode:
        verify_map = {p: (s, size_hash_groups[(s, h)]) for (
            s, h), paths in size_hash_groups.items() for p in paths if len(paths) > 1}
        verify_results = batch_hash_files(
            list(verify_map.keys()), -1, False, threads)

        duplicates = defaultdict(list)
        for path, hash in verify_results.items():
            size, _ = verify_map[path]
            duplicates[(size, hash)].append(path)

        return {k: v for k, v in duplicates.items() if len(v) > 1}
    else:
        return {k: v for k, v in size_hash_groups.items() if len(v) > 1}
