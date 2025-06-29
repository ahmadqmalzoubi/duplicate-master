import pytest
import os
from duplicatemaster.scanner import get_files_recursively

class DummyLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass


def create_files(base, files):
    for f in files:
        path = base / f
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test")


def test_get_files_recursively_basic(tmp_path):
    files = ["a.txt", "b.txt", "subdir/c.txt"]
    create_files(tmp_path, files)
    result = list(get_files_recursively(str(tmp_path), [], [], False, DummyLogger()))
    found = sorted([os.path.relpath(f, tmp_path) for f in result])
    assert sorted(files) == found

def test_get_files_recursively_exclude_pattern(tmp_path):
    files = ["a.txt", "b.log", "c.txt"]
    create_files(tmp_path, files)
    result = list(get_files_recursively(str(tmp_path), ["*.log"], [], False, DummyLogger()))
    found = sorted([os.path.basename(f) for f in result])
    assert "b.log" not in found
    assert "a.txt" in found and "c.txt" in found

def test_get_files_recursively_hidden(tmp_path):
    files = [".hidden.txt", "visible.txt"]
    create_files(tmp_path, files)
    # Should not include hidden by default
    result = list(get_files_recursively(str(tmp_path), [], [], True, DummyLogger()))
    found = [os.path.basename(f) for f in result]
    assert ".hidden.txt" not in found
    # Should include hidden if requested
    result = list(get_files_recursively(str(tmp_path), [], [], False, DummyLogger()))
    found = [os.path.basename(f) for f in result]
    assert ".hidden.txt" in found

def test_get_files_recursively_exclude_dir(tmp_path):
    files = ["a.txt", "skipdir/b.txt", "keepdir/c.txt"]
    create_files(tmp_path, files)
    result = list(get_files_recursively(str(tmp_path), [], ["skipdir"], False, DummyLogger()))
    found = [os.path.relpath(f, tmp_path) for f in result]
    assert "skipdir/b.txt" not in found
    assert "a.txt" in found and "keepdir/c.txt" in found 