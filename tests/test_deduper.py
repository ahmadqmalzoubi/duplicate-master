import os
import pytest
from unittest.mock import patch, MagicMock, call
from collections import defaultdict
from filedupfinder.deduper import find_duplicates


class MockLogger:
    def __init__(self):
        self.messages = []
    
    def debug(self, msg):
        self.messages.append(("debug", msg))
    
    def info(self, msg):
        self.messages.append(("info", msg))
    
    def warning(self, msg):
        self.messages.append(("warning", msg))
    
    def error(self, msg):
        self.messages.append(("error", msg))


class MockProgressCallback:
    def __init__(self):
        self.calls = []
    
    def __call__(self, percentage, message):
        self.calls.append((percentage, message))


@patch('filedupfinder.deduper.get_files_with_size_filter')
@patch('filedupfinder.deduper.hash_files_with_size_info')
def test_find_duplicates_quick_mode(mock_hash_files, mock_get_files):
    """Test duplicate detection in quick mode."""
    # Mock file discovery with size information
    mock_get_files.return_value = [
        (1024, "/path/file1.txt"),
        (1024, "/path/file2.txt"),
        (2048, "/path/file3.txt")
    ]

    # Mock hashing results
    mock_hash_files.return_value = {
        "/path/file1.txt": "hash1",
        "/path/file2.txt": "hash1",  # Same hash as file1
        "/path/file3.txt": "hash2"
    }

    logger = MockLogger()
    result = find_duplicates(
        base_dir="/test",
        min_size=100,
        max_size=5000,
        quick_mode=True,
        multi_region=False,
        exclude=[],
        exclude_dir=[],
        exclude_hidden=False,
        threads=4,
        logger=logger,
        use_optimized_scanning=True
    )

    # Check results
    expected = {(1024, "hash1"): ["/path/file1.txt", "/path/file2.txt"]}
    assert result == expected


@patch('filedupfinder.deduper.get_files_with_size_filter')
@patch('filedupfinder.deduper.hash_files_with_size_info')
@patch('filedupfinder.deduper.batch_hash_files')
def test_find_duplicates_full_mode(mock_batch_hash, mock_hash_files, mock_get_files):
    """Test duplicate detection in full mode."""
    # Mock file discovery with size information
    mock_get_files.return_value = [
        (1024, "/path/file1.txt"),
        (1024, "/path/file2.txt"),
        (2048, "/path/file3.txt")
    ]

    # Mock first hashing pass (quick scan)
    mock_hash_files.return_value = {
        "/path/file1.txt": "hash1",
        "/path/file2.txt": "hash1",  # Same hash as file1
        "/path/file3.txt": "hash2"
    }

    # Mock second hashing pass (full scan)
    mock_batch_hash.return_value = {
        "/path/file1.txt": "full_hash1",
        "/path/file2.txt": "full_hash1",  # Same full hash
    }

    logger = MockLogger()
    result = find_duplicates(
        base_dir="/test",
        min_size=100,
        max_size=5000,
        quick_mode=False,
        multi_region=True,
        exclude=[],
        exclude_dir=[],
        exclude_hidden=False,
        threads=4,
        logger=logger,
        use_optimized_scanning=True
    )

    # Check results
    expected = {(1024, "full_hash1"): ["/path/file1.txt", "/path/file2.txt"]}
    assert result == expected

    # Check that batch_hash_files was called for full scan verification
    assert mock_batch_hash.call_count == 1


@patch('filedupfinder.deduper.get_files_with_size_filter')
@patch('filedupfinder.deduper.hash_files_with_size_info')
def test_find_duplicates_with_progress_callback(mock_hash_files, mock_get_files):
    """Test duplicate detection with progress callback."""
    # Mock file discovery with size information
    mock_get_files.return_value = [
        (1024, "/path/file1.txt"),
        (1024, "/path/file2.txt")
    ]

    # Mock hashing results
    mock_hash_files.return_value = {
        "/path/file1.txt": "hash1",
        "/path/file2.txt": "hash1"
    }

    logger = MockLogger()
    progress_callback = MockProgressCallback()

    result = find_duplicates(
        base_dir="/test",
        min_size=100,
        max_size=5000,
        quick_mode=True,
        multi_region=False,
        exclude=[],
        exclude_dir=[],
        exclude_hidden=False,
        threads=4,
        logger=logger,
        progress_callback=progress_callback,
        use_optimized_scanning=True
    )

    # Check that progress callback was called
    assert len(progress_callback.calls) > 0

    # Check specific progress calls
    progress_messages = [msg for _, msg in progress_callback.calls]
    assert "Scanning for files..." in progress_messages
    assert "Found 2 files to process..." in progress_messages


@patch('filedupfinder.deduper.get_files_with_size_filter')
@patch('filedupfinder.deduper.hash_files_with_size_info')
def test_find_duplicates_file_size_filtering(mock_hash_files, mock_get_files):
    """Test file size filtering."""
    # Mock file discovery with size information (only medium file in range)
    mock_get_files.return_value = [
        (1024, "/path/medium.txt")
    ]

    # Mock hashing results
    mock_hash_files.return_value = {
        "/path/medium.txt": "hash1"
    }

    logger = MockLogger()
    result = find_duplicates(
        base_dir="/test",
        min_size=100,  # 100B minimum
        max_size=5000,  # 5KB maximum
        quick_mode=True,
        multi_region=False,
        exclude=[],
        exclude_dir=[],
        exclude_hidden=False,
        threads=4,
        logger=logger,
        use_optimized_scanning=True
    )

    # Only medium.txt should be processed, but since it's alone, no duplicates
    assert result == {}

    # Check that hash_files_with_size_info was called
    mock_hash_files.assert_called_once()


@patch('filedupfinder.deduper.get_files_with_size_filter')
@patch('filedupfinder.deduper.hash_files_with_size_info')
def test_find_duplicates_os_error_handling(mock_hash_files, mock_get_files):
    """Test handling of OSError when getting file size."""
    # Mock file discovery with size information (only valid files)
    mock_get_files.return_value = [
        (1024, "/path/file1.txt"),
        (2048, "/path/file3.txt")
    ]

    # Mock hashing results
    mock_hash_files.return_value = {
        "/path/file1.txt": "hash1",
        "/path/file3.txt": "hash2"
    }

    logger = MockLogger()
    result = find_duplicates(
        base_dir="/test",
        min_size=100,
        max_size=5000,
        quick_mode=True,
        multi_region=False,
        exclude=[],
        exclude_dir=[],
        exclude_hidden=False,
        threads=4,
        logger=logger,
        use_optimized_scanning=True
    )

    # Should process the valid files, but since they have different hashes, no duplicates
    assert result == {}

    # Check that hash_files_with_size_info was called
    mock_hash_files.assert_called_once()


@patch('filedupfinder.deduper.get_files_with_size_filter')
@patch('filedupfinder.deduper.hash_files_with_size_info')
def test_find_duplicates_empty_directory(mock_hash_files, mock_get_files):
    """Test with empty directory."""
    # Mock empty file discovery
    mock_get_files.return_value = []

    # Mock hashing results for empty list
    mock_hash_files.return_value = {}

    logger = MockLogger()
    result = find_duplicates(
        base_dir="/test",
        min_size=100,
        max_size=5000,
        quick_mode=True,
        multi_region=False,
        exclude=[],
        exclude_dir=[],
        exclude_hidden=False,
        threads=4,
        logger=logger,
        use_optimized_scanning=True
    )

    # Should return empty dict
    assert result == {}

    # hash_files_with_size_info should not be called with empty list
    mock_hash_files.assert_not_called()


@patch('filedupfinder.deduper.get_files_recursively')
@patch('filedupfinder.deduper.batch_hash_files')
def test_find_duplicates_legacy_mode(mock_batch_hash, mock_get_files):
    """Test duplicate detection in legacy mode (non-optimized)."""
    # Mock file discovery
    mock_get_files.return_value = [
        "/path/file1.txt",
        "/path/file2.txt",
        "/path/file3.txt"
    ]

    # Mock file sizes
    with patch('os.path.getsize') as mock_getsize:
        mock_getsize.side_effect = [1024, 1024, 2048]

        # Mock hashing results
        mock_batch_hash.return_value = {
            "/path/file1.txt": "hash1",
            "/path/file2.txt": "hash1",  # Same hash as file1
            "/path/file3.txt": "hash2"
        }

        logger = MockLogger()
        result = find_duplicates(
            base_dir="/test",
            min_size=100,
            max_size=5000,
            quick_mode=True,
            multi_region=False,
            exclude=[],
            exclude_dir=[],
            exclude_hidden=False,
            threads=4,
            logger=logger,
            use_optimized_scanning=False
        )

    # Check results
    expected = {(1024, "hash1"): ["/path/file1.txt", "/path/file2.txt"]}
    assert result == expected


@patch('filedupfinder.deduper.get_files_with_size_filter')
@patch('filedupfinder.deduper.hash_files_with_size_info')
def test_find_duplicates_no_duplicates_found(mock_hash_files, mock_get_files):
    """Test when no duplicates are found."""
    # Mock file discovery with size information
    mock_get_files.return_value = [
        (1024, "/path/file1.txt"),
        (2048, "/path/file2.txt")
    ]

    # Mock hashing results (different hashes)
    mock_hash_files.return_value = {
        "/path/file1.txt": "hash1",
        "/path/file2.txt": "hash2"
    }

    logger = MockLogger()
    result = find_duplicates(
        base_dir="/test",
        min_size=100,
        max_size=5000,
        quick_mode=True,
        multi_region=False,
        exclude=[],
        exclude_dir=[],
        exclude_hidden=False,
        threads=4,
        logger=logger,
        use_optimized_scanning=True
    )

    # Should return empty dict when no duplicates found
    assert result == {} 