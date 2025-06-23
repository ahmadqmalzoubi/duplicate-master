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


@patch('filedupfinder.deduper.get_files_recursively')
@patch('filedupfinder.deduper.batch_hash_files')
def test_find_duplicates_quick_mode(mock_batch_hash, mock_get_files):
    """Test duplicate detection in quick mode."""
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
            logger=logger
        )
    
    # Check results
    expected = {(1024, "hash1"): ["/path/file1.txt", "/path/file2.txt"]}
    assert result == expected
    
    # Check that batch_hash_files was called correctly
    mock_batch_hash.assert_called_once()
    call_args = mock_batch_hash.call_args
    assert call_args[0][0] == ["/path/file1.txt", "/path/file2.txt", "/path/file3.txt"]
    assert call_args[0][1] == 4096  # buffer_size for quick mode
    assert call_args[0][2] is False  # multi_region should be False in quick mode


@patch('filedupfinder.deduper.get_files_recursively')
@patch('filedupfinder.deduper.batch_hash_files')
def test_find_duplicates_full_mode(mock_batch_hash, mock_get_files):
    """Test duplicate detection in full mode."""
    # Mock file discovery
    mock_get_files.return_value = [
        "/path/file1.txt",
        "/path/file2.txt",
        "/path/file3.txt"
    ]
    
    # Mock file sizes
    with patch('os.path.getsize') as mock_getsize:
        mock_getsize.side_effect = [1024, 1024, 2048]
        
        # Mock first hashing pass (quick scan)
        mock_batch_hash.side_effect = [
            {
                "/path/file1.txt": "hash1",
                "/path/file2.txt": "hash1",  # Same hash as file1
                "/path/file3.txt": "hash2"
            },
            # Mock second hashing pass (full scan)
            {
                "/path/file1.txt": "full_hash1",
                "/path/file2.txt": "full_hash1",  # Same full hash
            }
        ]
        
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
            logger=logger
        )
    
    # Check results
    expected = {(1024, "full_hash1"): ["/path/file1.txt", "/path/file2.txt"]}
    assert result == expected
    
    # Check that batch_hash_files was called twice (quick scan + full scan)
    assert mock_batch_hash.call_count == 2
    
    # First call (quick scan)
    first_call = mock_batch_hash.call_args_list[0]
    assert first_call[0][1] == "auto"  # buffer_size for full mode
    assert first_call[0][2] is True  # multi_region should be True
    
    # Second call (full scan)
    second_call = mock_batch_hash.call_args_list[1]
    assert second_call[0][1] == -1  # buffer_size for full scan
    assert second_call[0][2] is False  # multi_region should be False for full scan


@patch('filedupfinder.deduper.get_files_recursively')
@patch('filedupfinder.deduper.batch_hash_files')
def test_find_duplicates_with_progress_callback(mock_batch_hash, mock_get_files):
    """Test duplicate detection with progress callback."""
    # Mock file discovery
    mock_get_files.return_value = ["/path/file1.txt", "/path/file2.txt"]
    
    # Mock file sizes
    with patch('os.path.getsize') as mock_getsize:
        mock_getsize.side_effect = [1024, 1024]
        
        # Mock hashing results
        mock_batch_hash.return_value = {
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
            progress_callback=progress_callback
        )
    
    # Check that progress callback was called
    assert len(progress_callback.calls) > 0
    
    # Check specific progress calls
    progress_messages = [msg for _, msg in progress_callback.calls]
    assert "Scanning for files..." in progress_messages
    assert "Hashing files (Quick Scan)..." in progress_messages
    assert "Scan complete." in progress_messages


@patch('filedupfinder.deduper.get_files_recursively')
@patch('filedupfinder.deduper.batch_hash_files')
def test_find_duplicates_no_duplicates_found(mock_batch_hash, mock_get_files):
    """Test when no duplicates are found."""
    # Mock file discovery
    mock_get_files.return_value = ["/path/file1.txt", "/path/file2.txt"]
    
    # Mock file sizes
    with patch('os.path.getsize') as mock_getsize:
        mock_getsize.side_effect = [1024, 2048]
        
        # Mock hashing results (different hashes)
        mock_batch_hash.return_value = {
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
            logger=logger
        )
    
    # Should return empty dict when no duplicates found
    assert result == {}


@patch('filedupfinder.deduper.get_files_recursively')
@patch('filedupfinder.deduper.batch_hash_files')
def test_find_duplicates_file_size_filtering(mock_batch_hash, mock_get_files):
    """Test file size filtering."""
    # Mock file discovery
    mock_get_files.return_value = [
        "/path/small.txt",
        "/path/medium.txt",
        "/path/large.txt"
    ]
    
    # Mock file sizes
    with patch('os.path.getsize') as mock_getsize:
        mock_getsize.side_effect = [50, 1024, 10000]  # 50B, 1KB, 10KB
        
        # Mock hashing results
        mock_batch_hash.return_value = {
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
            logger=logger
        )
    
    # Only medium.txt should be processed (within size range)
    assert result == {}
    
    # Check that batch_hash_files was called with only the medium file
    mock_batch_hash.assert_called_once()
    call_args = mock_batch_hash.call_args
    assert call_args[0][0] == ["/path/medium.txt"]


@patch('filedupfinder.deduper.get_files_recursively')
@patch('filedupfinder.deduper.batch_hash_files')
def test_find_duplicates_os_error_handling(mock_batch_hash, mock_get_files):
    """Test handling of OSError when getting file size."""
    # Mock file discovery
    mock_get_files.return_value = [
        "/path/file1.txt",
        "/path/file2.txt",
        "/path/file3.txt"
    ]
    
    # Mock file sizes with one OSError
    with patch('os.path.getsize') as mock_getsize:
        mock_getsize.side_effect = [1024, OSError("Permission denied"), 2048]
        
        # Mock hashing results
        mock_batch_hash.return_value = {
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
            logger=logger
        )
    
    # Should skip the file with OSError and process the others
    assert result == {}
    
    # Check that batch_hash_files was called with only the valid files
    mock_batch_hash.assert_called_once()
    call_args = mock_batch_hash.call_args
    assert call_args[0][0] == ["/path/file1.txt", "/path/file3.txt"]


@patch('filedupfinder.deduper.get_files_recursively')
@patch('filedupfinder.deduper.batch_hash_files')
def test_find_duplicates_empty_directory(mock_batch_hash, mock_get_files):
    """Test with empty directory."""
    # Mock empty file discovery
    mock_get_files.return_value = []
    
    # Mock hashing results for empty list
    mock_batch_hash.return_value = {}
    
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
        logger=logger
    )
    
    # Should return empty dict
    assert result == {}
    
    # batch_hash_files should be called with empty list
    mock_batch_hash.assert_called_once()
    call_args = mock_batch_hash.call_args
    assert call_args[0][0] == []  # Empty list of files 