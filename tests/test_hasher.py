import os
import pytest
from filedupfinder.hasher import blake2bsum, batch_hash_files, DEFAULT_THREADS


def test_blake2bsum_basic(tmp_path):
    file = tmp_path / "file.txt"
    file.write_text("hello world")
    h = blake2bsum(str(file), buffer_size=-1, multi_region=False)
    assert isinstance(h, str)
    assert len(h) == 128  # blake2b hex digest length


def test_blake2bsum_nonexistent():
    with pytest.raises(Exception):
        blake2bsum("/nonexistent/file.txt", buffer_size=-1, multi_region=False)


def test_batch_hash_files(tmp_path):
    files = []
    for i in range(3):
        f = tmp_path / f"f{i}.txt"
        f.write_text(f"data{i}")
        files.append(str(f))
    hashes = batch_hash_files(files, buffer_size=-1, multi_region=False, threads=DEFAULT_THREADS)
    assert isinstance(hashes, dict)
    assert set(hashes.keys()) == set(files)
    for v in hashes.values():
        assert isinstance(v, str)
        assert len(v) == 128 