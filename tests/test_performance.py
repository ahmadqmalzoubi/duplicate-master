import pytest
import time
import tempfile
import os
from pathlib import Path
from duplicatemaster.scanner import get_files_recursively, get_files_with_size_filter, _get_files_parallel, _get_files_sequential
from duplicatemaster.hasher import blake2bsum, batch_hash_files, hash_files_with_size_info, _hash_with_memory_map, _hash_with_file_reading
from duplicatemaster.benchmark import PerformanceBenchmark
from duplicatemaster.logger import setup_logger


class TestOptimizedScanner:
    """Test cases for optimized scanner functionality."""

    def test_parallel_vs_sequential_scanning(self):
        """Test that parallel and sequential scanning produce the same results."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            
            # Create test directory structure
            (base_dir / "dir1").mkdir()
            (base_dir / "dir2").mkdir()
            (base_dir / "dir1" / "subdir").mkdir()
            
            # Create test files
            test_files = [
                base_dir / "file1.txt",
                base_dir / "dir1" / "file2.txt",
                base_dir / "dir1" / "subdir" / "file3.txt",
                base_dir / "dir2" / "file4.txt",
            ]
            
            for file_path in test_files:
                file_path.write_text(f"Content for {file_path.name}")
            
            logger = setup_logger(type('Args', (), {'loglevel': 'info', 'logfile': None})())
            
            # Get results from both methods
            sequential_files = set(_get_files_sequential(str(base_dir), [], [], False, logger))
            parallel_files = set(_get_files_parallel(str(base_dir), [], [], False, logger, max_workers=2))
            
            # Results should be identical
            assert sequential_files == parallel_files
            assert len(sequential_files) == 4

    def test_size_filtered_scanning(self):
        """Test that size-filtered scanning works correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            
            # Create files of different sizes
            small_file = base_dir / "small.txt"
            medium_file = base_dir / "medium.txt"
            large_file = base_dir / "large.txt"
            
            small_file.write_text("small")
            medium_file.write_text("medium content" * 100)
            large_file.write_text("large content" * 1000)
            
            # Check actual file sizes
            small_size = small_file.stat().st_size
            medium_size = medium_file.stat().st_size
            large_size = large_file.stat().st_size
            
            logger = setup_logger(type('Args', (), {'loglevel': 'info', 'logfile': None})())
            
            # Test size filtering with actual file sizes
            min_size = small_size + 1  # Between small and medium
            max_size = large_size - 1  # Between medium and large
            
            files_with_size = list(get_files_with_size_filter(
                str(base_dir), [], [], False, min_size, max_size, logger
            ))
            
            # Should only include medium file
            assert len(files_with_size) == 1
            assert files_with_size[0][1] == str(medium_file)

    def test_parallel_scanning_with_exclusions(self):
        """Test parallel scanning with file and directory exclusions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            
            # Create test structure
            (base_dir / "include_dir").mkdir()
            (base_dir / "exclude_dir").mkdir()
            
            # Create files
            (base_dir / "include_dir" / "file1.txt").write_text("content")
            (base_dir / "exclude_dir" / "file2.txt").write_text("content")
            (base_dir / "file3.tmp").write_text("content")  # Should be excluded
            
            logger = setup_logger(type('Args', (), {'loglevel': 'info', 'logfile': None})())
            
            files = set(_get_files_parallel(
                str(base_dir), 
                ["*.tmp"],  # Exclude .tmp files
                ["exclude_dir"],  # Exclude directory
                False, 
                logger, 
                max_workers=2
            ))
            
            # Should only include file1.txt
            assert len(files) == 1
            assert str(base_dir / "include_dir" / "file1.txt") in files


class TestOptimizedHasher:
    """Test cases for optimized hasher functionality."""

    def test_optimized_buffer_sizes(self):
        """Test that optimized buffer sizes work correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files of different sizes
            small_file = Path(temp_dir) / "small.txt"
            medium_file = Path(temp_dir) / "medium.txt"
            large_file = Path(temp_dir) / "large.txt"
            
            small_file.write_text("small content")
            medium_file.write_text("medium content" * 1000)
            large_file.write_text("large content" * 100000)
            
            # Test auto buffer size selection
            small_hash = blake2bsum(str(small_file), "auto", False)
            medium_hash = blake2bsum(str(medium_file), "auto", False)
            large_hash = blake2bsum(str(large_file), "auto", False)
            
            # All hashes should be valid
            assert len(small_hash) == 128
            assert len(medium_hash) == 128
            assert len(large_hash) == 128

    def test_memory_mapping(self):
        """Test memory mapping functionality for large files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file large enough to trigger memory mapping
            large_file = Path(temp_dir) / "large.txt"
            large_content = "large content " * 1000000  # ~15MB
            large_file.write_text(large_content)
            
            # Test memory mapping
            hash1 = _hash_with_memory_map(str(large_file), False)
            hash2 = _hash_with_file_reading(str(large_file), large_file.stat().st_size, -1, False)
            
            # Both methods should produce the same hash
            assert hash1 == hash2
            assert len(hash1) == 128

    def test_hash_files_with_size_info(self):
        """Test optimized hashing with pre-computed size information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            files_with_size = []
            for i in range(5):
                file_path = Path(temp_dir) / f"file{i}.txt"
                content = f"content {i}" * 100
                file_path.write_text(content)
                files_with_size.append((file_path.stat().st_size, str(file_path)))
            
            # Test optimized hashing
            results = hash_files_with_size_info(
                files_with_size, "auto", False, 2
            )
            
            # All files should be hashed
            assert len(results) == 5
            for path in results.values():
                assert len(path) == 128

    def test_batch_hashing_optimizations(self):
        """Test batch hashing optimizations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            paths = []
            for i in range(10):
                file_path = Path(temp_dir) / f"file{i}.txt"
                file_path.write_text(f"content {i}")
                paths.append(str(file_path))
            
            # Test with different batch sizes
            results1 = batch_hash_files(paths, "auto", False, 2, batch_size=5)
            results2 = batch_hash_files(paths, "auto", False, 2, batch_size=None)
            
            # Results should be identical
            assert results1 == results2
            assert len(results1) == 10


class TestPerformanceBenchmark:
    """Test cases for performance benchmarking."""

    def test_benchmark_creation(self):
        """Test benchmark object creation and basic functionality."""
        benchmark = PerformanceBenchmark()
        assert benchmark is not None
        assert hasattr(benchmark, 'create_test_data')
        assert hasattr(benchmark, 'benchmark_scan')

    def test_test_data_creation(self):
        """Test test data creation functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            benchmark = PerformanceBenchmark()
            stats = benchmark.create_test_data(Path(temp_dir), num_files=10, num_duplicates=5)
            
            assert stats['unique_files'] == 10
            assert stats['duplicate_files'] == 5
            assert stats['total_files'] == 15
            assert stats['subdirectories'] == 5

    def test_single_benchmark(self):
        """Test single benchmark execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            benchmark = PerformanceBenchmark()
            
            # Create test data
            benchmark.create_test_data(Path(temp_dir), num_files=5, num_duplicates=2)
            
            # Run benchmark
            result = benchmark.benchmark_scan(
                str(temp_dir),
                "Test Scan",
                use_optimized=True,
                threads=2,
                quick_mode=True
            )
            
            assert result['scan_name'] == "Test Scan"
            assert result['duration'] > 0
            assert result['duplicates_found'] >= 0
            assert result['use_optimized'] is True

    def test_memory_usage_tracking(self):
        """Test memory usage tracking."""
        benchmark = PerformanceBenchmark()
        memory = benchmark._get_memory_usage()
        
        # Memory usage should be a non-negative number
        assert isinstance(memory, float)
        assert memory >= 0.0 