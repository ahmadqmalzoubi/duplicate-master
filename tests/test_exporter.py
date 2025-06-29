import pytest
import json
import csv
import os
from unittest.mock import MagicMock
from duplicatemaster.exporter import export_results


class MockArgs:
    def __init__(self, json_out=None, csv_out=None):
        self.json_out = json_out
        self.csv_out = csv_out


class MockLogger:
    def __init__(self):
        self.info_messages = []
        self.error_messages = []
    
    def info(self, message):
        self.info_messages.append(message)
    
    def error(self, message):
        self.error_messages.append(message)


def test_export_results_json_only(tmp_path):
    """Test JSON export functionality."""
    json_file = tmp_path / "test.json"
    args = MockArgs(json_out=str(json_file))
    logger = MockLogger()
    
    duplicates = {
        (1024, "hash1"): ["/path/file1.txt", "/path/file2.txt"],
        (2048, "hash2"): ["/path/file3.txt"]
    }
    
    export_results(duplicates, args, logger)
    
    # Check that file was created
    assert json_file.exists()
    
    # Check JSON content
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    assert len(data) == 2
    assert data[0]["size_bytes"] == 1024
    assert data[0]["hash"] == "hash1"
    assert data[0]["paths"] == ["/path/file1.txt", "/path/file2.txt"]
    assert data[1]["size_bytes"] == 2048
    assert data[1]["hash"] == "hash2"
    assert data[1]["paths"] == ["/path/file3.txt"]
    
    # Check logger messages
    assert any("Written to JSON" in msg for msg in logger.info_messages)
    assert len(logger.error_messages) == 0


def test_export_results_csv_only(tmp_path):
    """Test CSV export functionality."""
    csv_file = tmp_path / "test.csv"
    args = MockArgs(csv_out=str(csv_file))
    logger = MockLogger()
    
    duplicates = {
        (1024, "hash1"): ["/path/file1.txt", "/path/file2.txt"],
        (2048, "hash2"): ["/path/file3.txt"]
    }
    
    export_results(duplicates, args, logger)
    
    # Check that file was created
    assert csv_file.exists()
    
    # Check CSV content
    with open(csv_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    assert len(rows) == 3  # 2 files in first group + 1 file in second group
    assert rows[0]["size_bytes"] == "1024"
    assert rows[0]["hash"] == "hash1"
    assert rows[0]["path"] == "/path/file1.txt"
    assert rows[1]["size_bytes"] == "1024"
    assert rows[1]["hash"] == "hash1"
    assert rows[1]["path"] == "/path/file2.txt"
    assert rows[2]["size_bytes"] == "2048"
    assert rows[2]["hash"] == "hash2"
    assert rows[2]["path"] == "/path/file3.txt"
    
    # Check logger messages
    assert any("Written to CSV" in msg for msg in logger.info_messages)
    assert len(logger.error_messages) == 0


def test_export_results_both_formats(tmp_path):
    """Test both JSON and CSV export together."""
    json_file = tmp_path / "test.json"
    csv_file = tmp_path / "test.csv"
    args = MockArgs(json_out=str(json_file), csv_out=str(csv_file))
    logger = MockLogger()
    
    duplicates = {
        (1024, "hash1"): ["/path/file1.txt", "/path/file2.txt"]
    }
    
    export_results(duplicates, args, logger)
    
    # Check that both files were created
    assert json_file.exists()
    assert csv_file.exists()
    
    # Check logger messages
    assert any("Written to JSON" in msg for msg in logger.info_messages)
    assert any("Written to CSV" in msg for msg in logger.info_messages)
    assert len(logger.error_messages) == 0


def test_export_results_empty_duplicates(tmp_path):
    """Test export with empty duplicates dictionary."""
    json_file = tmp_path / "test.json"
    csv_file = tmp_path / "test.csv"
    args = MockArgs(json_out=str(json_file), csv_out=str(csv_file))
    logger = MockLogger()
    
    duplicates = {}
    
    export_results(duplicates, args, logger)
    
    # Check that files were created (even if empty)
    assert json_file.exists()
    assert csv_file.exists()
    
    # Check JSON content
    with open(json_file, 'r') as f:
        data = json.load(f)
    assert data == []
    
    # Check CSV content (should have header only)
    with open(csv_file, 'r', newline='') as f:
        content = f.read()
    assert "size_bytes,hash,path" in content
    assert content.count('\n') == 1  # Only header line
    
    # Check logger messages
    assert any("Written to JSON" in msg for msg in logger.info_messages)
    assert any("Written to CSV" in msg for msg in logger.info_messages)
    assert len(logger.error_messages) == 0


def test_export_results_no_output_specified():
    """Test export when no output files are specified."""
    args = MockArgs()  # No json_out or csv_out
    logger = MockLogger()
    
    duplicates = {
        (1024, "hash1"): ["/path/file1.txt", "/path/file2.txt"]
    }
    
    export_results(duplicates, args, logger)
    
    # Should not crash and should not log any messages
    assert len(logger.info_messages) == 0
    assert len(logger.error_messages) == 0


def test_export_results_json_error_handling(tmp_path):
    """Test JSON export error handling."""
    # Create a directory with the same name as the file to cause an error
    json_file = tmp_path / "test.json"
    json_file.mkdir()  # Make it a directory instead of a file
    
    args = MockArgs(json_out=str(json_file))
    logger = MockLogger()
    
    duplicates = {
        (1024, "hash1"): ["/path/file1.txt", "/path/file2.txt"]
    }
    
    export_results(duplicates, args, logger)
    
    # Should log an error
    assert len(logger.error_messages) == 1
    assert "JSON export failed" in logger.error_messages[0]


def test_export_results_csv_error_handling(tmp_path):
    """Test CSV export error handling."""
    # Create a directory with the same name as the file to cause an error
    csv_file = tmp_path / "test.csv"
    csv_file.mkdir()  # Make it a directory instead of a file
    
    args = MockArgs(csv_out=str(csv_file))
    logger = MockLogger()
    
    duplicates = {
        (1024, "hash1"): ["/path/file1.txt", "/path/file2.txt"]
    }
    
    export_results(duplicates, args, logger)
    
    # Should log an error
    assert len(logger.error_messages) == 1
    assert "CSV export failed" in logger.error_messages[0] 