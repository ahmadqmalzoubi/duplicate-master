import os
import pytest
from typing import Any
from unittest.mock import patch, MagicMock, mock_open
from filedupfinder.deletion import delete_files, handle_deletion


class MockLogger:
    def __init__(self):
        self.info_messages = []
        self.error_messages = []
        self.warning_messages = []
    
    def info(self, message):
        self.info_messages.append(message)
    
    def error(self, message):
        self.error_messages.append(message)
    
    def warning(self, message):
        self.warning_messages.append(message)


class MockArgs:
    def __init__(self, force=False, dry_run=False, interactive=False):
        self.force = force
        self.dry_run = dry_run
        self.interactive = interactive


def test_delete_files_dry_run(tmp_path):
    """Test delete_files with dry run mode."""
    # Create test files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("test content 1")
    file2.write_text("test content 2")
    
    files_to_delete = [str(file1), str(file2)]
    logger: Any = MockLogger()
    
    delete_files(files_to_delete, dry_run=True, logger_obj=logger)
    
    # Files should still exist
    assert file1.exists()
    assert file2.exists()
    
    # Should log dry run messages
    assert len(logger.info_messages) == 2
    assert any("[DRY-RUN] Would delete:" in msg for msg in logger.info_messages)
    assert len(logger.error_messages) == 0


def test_delete_files_actual_deletion(tmp_path):
    """Test delete_files with actual deletion."""
    # Create test files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("test content 1")
    file2.write_text("test content 2")
    
    files_to_delete = [str(file1), str(file2)]
    logger: Any = MockLogger()
    
    delete_files(files_to_delete, dry_run=False, logger_obj=logger)
    
    # Files should be deleted
    assert not file1.exists()
    assert not file2.exists()
    
    # Should log deletion messages
    assert len(logger.info_messages) == 2
    assert any("Deleted:" in msg for msg in logger.info_messages)
    assert len(logger.error_messages) == 0


def test_delete_files_deletion_error(tmp_path):
    """Test delete_files when deletion fails."""
    # Create one file and one non-existent file
    file1 = tmp_path / "file1.txt"
    file1.write_text("test content")
    non_existent_file = tmp_path / "non_existent.txt"
    
    files_to_delete = [str(file1), str(non_existent_file)]
    logger: Any = MockLogger()
    
    delete_files(files_to_delete, dry_run=False, logger_obj=logger)
    
    # First file should be deleted, second should fail
    assert not file1.exists()
    
    # Should log success and error messages
    assert len(logger.info_messages) == 1
    assert len(logger.error_messages) == 1
    assert any("Deleted:" in msg for msg in logger.info_messages)
    assert any("Failed to delete" in msg for msg in logger.error_messages)


def test_handle_deletion_force_mode(tmp_path):
    """Test handle_deletion with force mode."""
    # Create test files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file3 = tmp_path / "file3.txt"
    file1.write_text("test content 1")
    file2.write_text("test content 2")
    file3.write_text("test content 3")
    
    duplicates = {
        (1024, "hash1"): [str(file1), str(file2)],
        (2048, "hash2"): [str(file3)]
    }
    
    args = MockArgs(force=True, dry_run=True)
    logger: Any = MockLogger()
    
    handle_deletion(duplicates, args, logger)
    
    # Files should still exist (dry run)
    assert file1.exists()
    assert file2.exists()
    assert file3.exists()
    
    # Should log dry run messages for duplicates only
    assert len(logger.info_messages) == 1  # Only file2 should be marked for deletion
    assert any("[DRY-RUN] Would delete:" in msg for msg in logger.info_messages)


def test_handle_deletion_dry_run_mode(tmp_path):
    """Test handle_deletion with dry run mode."""
    # Create test files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("test content 1")
    file2.write_text("test content 2")
    
    duplicates = {
        (1024, "hash1"): [str(file1), str(file2)]
    }
    
    args = MockArgs(force=False, dry_run=True)
    logger: Any = MockLogger()
    
    # Mock input to confirm deletion (though it shouldn't be called with dry_run=True)
    with patch('builtins.input', return_value='y'):
        handle_deletion(duplicates, args, logger)
    
    # Files should still exist (dry run)
    assert file1.exists()
    assert file2.exists()
    
    # Should log dry run messages (only the deletion, no confirmation needed)
    assert len(logger.info_messages) == 1  # Only dry run deletion message
    assert any("Would delete:" in msg for msg in logger.info_messages)


def test_handle_deletion_cancelled(tmp_path):
    """Test handle_deletion when user cancels."""
    # Create test files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("test content 1")
    file2.write_text("test content 2")
    
    duplicates = {
        (1024, "hash1"): [str(file1), str(file2)]
    }
    
    args = MockArgs(force=False, dry_run=False)
    logger: Any = MockLogger()
    
    # Mock input to cancel deletion
    with patch('builtins.input', return_value='n'):
        handle_deletion(duplicates, args, logger)
    
    # Files should still exist
    assert file1.exists()
    assert file2.exists()
    
    # Should log cancellation message
    assert len(logger.info_messages) == 1
    assert "Deletion cancelled." in logger.info_messages[0]


@patch('builtins.input')
@patch('builtins.print')
def test_handle_deletion_interactive_mode(mock_print, mock_input, tmp_path):
    """Test handle_deletion with interactive mode."""
    # Create test files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file3 = tmp_path / "file3.txt"
    file1.write_text("test content 1")
    file2.write_text("test content 2")
    file3.write_text("test content 3")
    
    duplicates = {
        (1024, "hash1"): [str(file1), str(file2), str(file3)]
    }
    
    args = MockArgs(force=True, dry_run=True, interactive=True)
    logger: Any = MockLogger()
    
    # Mock user input to delete all but first
    mock_input.return_value = 'a'
    
    handle_deletion(duplicates, args, logger)
    
    # Files should still exist (dry run)
    assert file1.exists()
    assert file2.exists()
    assert file3.exists()
    
    # Should log dry run messages for files 2 and 3
    assert len(logger.info_messages) == 2
    assert all("[DRY-RUN] Would delete:" in msg for msg in logger.info_messages)
    
    # Should print interactive prompts
    assert mock_print.called


@patch('builtins.input')
@patch('builtins.print')
def test_handle_deletion_interactive_skip(mock_print, mock_input, tmp_path):
    """Test handle_deletion interactive mode with skip."""
    # Create test files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("test content 1")
    file2.write_text("test content 2")
    
    duplicates = {
        (1024, "hash1"): [str(file1), str(file2)]
    }
    
    args = MockArgs(force=True, dry_run=True, interactive=True)
    logger: Any = MockLogger()
    
    # Mock user input to skip
    mock_input.return_value = 's'
    
    handle_deletion(duplicates, args, logger)
    
    # Files should still exist
    assert file1.exists()
    assert file2.exists()
    
    # Should not log any deletion messages
    assert len(logger.info_messages) == 0


@patch('builtins.input')
@patch('builtins.print')
def test_handle_deletion_interactive_invalid_input(mock_print, mock_input, tmp_path):
    """Test handle_deletion interactive mode with invalid input."""
    # Create test files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("test content 1")
    file2.write_text("test content 2")
    
    duplicates = {
        (1024, "hash1"): [str(file1), str(file2)]
    }
    
    args = MockArgs(force=True, dry_run=True, interactive=True)
    logger: Any = MockLogger()
    
    # Mock user input with invalid choice
    mock_input.return_value = 'invalid'
    
    handle_deletion(duplicates, args, logger)
    
    # Files should still exist
    assert file1.exists()
    assert file2.exists()
    
    # Should log warning about invalid input
    assert len(logger.warning_messages) == 1
    assert "Invalid input:" in logger.warning_messages[0]


def test_handle_deletion_single_file_groups(tmp_path):
    """Test handle_deletion with groups that have only one file."""
    # Create test files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("test content 1")
    file2.write_text("test content 2")
    
    # Group with single file should be skipped
    duplicates = {
        (1024, "hash1"): [str(file1)],  # Single file
        (2048, "hash2"): [str(file2)]   # Single file
    }
    
    args = MockArgs(force=True, dry_run=True)
    logger: Any = MockLogger()
    
    handle_deletion(duplicates, args, logger)
    
    # Files should still exist
    assert file1.exists()
    assert file2.exists()
    
    # Should not log any deletion messages (no duplicates to delete)
    assert len(logger.info_messages) == 0 