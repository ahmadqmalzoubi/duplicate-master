import os
import sys
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

DEFAULT_THREADS = min(32, (os.cpu_count() or 1) + 4)


def blake2bsum(filename, buffer_size, multi_region):
    h = hashlib.blake2b()
    file_size = os.path.getsize(filename)
    if buffer_size == "auto":
        buffer_size = -1 if file_size <= 8192 else 4096

    with open(filename, 'rb') as f:
        if multi_region and buffer_size != -1 and file_size > 12288:
            for pos in [0, file_size // 2 - 2048, max(0, file_size - 4096)]:
                f.seek(pos)
                h.update(f.read(4096))
        else:
            if buffer_size == -1:
                while chunk := f.read(8192):
                    h.update(chunk)
            else:
                h.update(f.read(buffer_size))
    return h.hexdigest()


def batch_hash_files(paths, buffer_size, multi_region, threads):
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(
            blake2bsum, p, buffer_size, multi_region): p for p in paths}
        results = {}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Hashing files", disable=(sys.stdout is None)):
            path = futures[future]
            try:
                results[path] = future.result()
            except Exception:
                continue
        return results
