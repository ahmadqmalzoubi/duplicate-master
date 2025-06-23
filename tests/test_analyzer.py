import pytest
from filedupfinder.analyzer import analyze_space_savings, format_bytes


class TestAnalyzer:
    """Test cases for the analyzer module."""

    def test_analyze_space_savings_empty(self):
        """Test space analysis with no duplicates."""
        duplicates = {}
        total, savings = analyze_space_savings(duplicates)
        assert total == 0
        assert savings == 0

    def test_analyze_space_savings_single_group(self):
        """Test space analysis with one duplicate group."""
        duplicates = {(1024, "hash1"): ["/path/file1.txt", "/path/file2.txt"]}
        total, savings = analyze_space_savings(duplicates)
        assert total == 2048  # 2 files * 1024 bytes
        assert savings == 1024  # 1 duplicate * 1024 bytes

    def test_analyze_space_savings_multiple_groups(self):
        """Test space analysis with multiple duplicate groups."""
        duplicates = {
            (1024, "hash1"): ["/path/file1.txt", "/path/file2.txt"],
            (2048, "hash2"): ["/path/file3.txt", "/path/file4.txt", "/path/file5.txt"],
        }
        total, savings = analyze_space_savings(duplicates)
        assert total == 8192  # (2*1024) + (3*2048) = 2048 + 6144 = 8192
        assert savings == 5120  # (1*1024) + (2*2048) = 1024 + 4096 = 5120

    def test_analyze_space_savings_no_duplicates(self):
        """Test space analysis with groups that have no duplicates (single files)."""
        duplicates = {
            (1024, "hash1"): ["/path/file1.txt"],
            (2048, "hash2"): ["/path/file2.txt"],
        }
        total, savings = analyze_space_savings(duplicates)
        assert total == 3072  # 1024 + 2048
        assert savings == 0  # No duplicates to remove

    def test_format_bytes_bytes(self):
        """Test byte formatting for small values."""
        assert format_bytes(0) == "0.0 bytes"
        assert format_bytes(512) == "512.0 bytes"
        assert format_bytes(1023) == "1023.0 bytes"

    def test_format_bytes_kilobytes(self):
        """Test byte formatting for KB values."""
        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(1536) == "1.5 KB"
        assert format_bytes(1024 * 1023) == "1023.0 KB"

    def test_format_bytes_megabytes(self):
        """Test byte formatting for MB values."""
        assert format_bytes(1024 * 1024) == "1.0 MB"
        assert format_bytes(1024 * 1024 * 2.5) == "2.5 MB"
        assert format_bytes(1024 * 1024 * 1023) == "1023.0 MB"

    def test_format_bytes_gigabytes(self):
        """Test byte formatting for GB values."""
        assert format_bytes(1024 * 1024 * 1024) == "1.0 GB"
        assert format_bytes(1024 * 1024 * 1024 * 2.5) == "2.5 GB"

    def test_format_bytes_terabytes(self):
        """Test byte formatting for TB values."""
        assert format_bytes(1024 * 1024 * 1024 * 1024) == "1.0 TB"
        assert format_bytes(1024 * 1024 * 1024 * 1024 * 2.5) == "2.5 TB"

    def test_format_bytes_petabytes(self):
        """Test byte formatting for very large values (PB)."""
        large_value = 1024 * 1024 * 1024 * 1024 * 1024
        assert format_bytes(large_value) == "1.0 PB"

    def test_format_bytes_edge_cases(self):
        """Test byte formatting edge cases."""
        # Test negative values (current behavior - stays as bytes)
        assert format_bytes(-1024) == "-1024.0 bytes"
        
        # Test very small decimal values
        assert format_bytes(1) == "1.0 bytes"
        assert format_bytes(0.5) == "0.5 bytes" 