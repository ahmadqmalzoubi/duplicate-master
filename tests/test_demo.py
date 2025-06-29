import pytest
import sys
import subprocess
import tempfile
from pathlib import Path
from duplicatemaster.demo import create_demo_files, run_demo_scan, print_demo_results, MockArgs
from duplicatemaster.logger import setup_logger


class TestDemo:
    """Test cases for demo functionality."""

    def test_create_demo_files(self):
        """Test that demo files are created correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            file_mapping = create_demo_files(base_dir)

            # Check that subdirectories were created
            assert (base_dir / "documents").exists()
            assert (base_dir / "pictures").exists()
            assert (base_dir / "backup").exists()

            # Check that files were created
            assert (base_dir / "documents" / "report.txt").exists()
            assert (base_dir / "documents" / "report_copy.txt").exists()
            assert (base_dir / "backup" / "report_backup.txt").exists()
            assert (base_dir / "pictures" / "vacation.jpg").exists()
            assert (base_dir / "pictures" / "vacation_copy.jpg").exists()

            # Check that file mapping is correct
            assert "sample_text" in file_mapping
            assert "image_data" in file_mapping
            assert "config_data" in file_mapping
            assert "large_content" in file_mapping

            # Check that each content type has the expected number of files
            assert len(file_mapping["sample_text"]) == 3  # 3 text file duplicates
            assert len(file_mapping["image_data"]) == 2   # 2 image file duplicates
            assert len(file_mapping["config_data"]) == 2  # 2 config file duplicates
            assert len(file_mapping["large_content"]) == 2  # 2 large file duplicates

    def test_run_demo_scan(self):
        """Test that demo scan finds duplicates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            
            # Create demo files
            file_mapping = create_demo_files(base_dir)
            
            # Set up logger
            args = MockArgs()
            logger = setup_logger(args)
            
            # Run scan
            duplicates = run_demo_scan(str(base_dir), logger)
            
            # Check that duplicates were found
            assert len(duplicates) > 0
            
            # Check that we found the expected number of groups
            # We should have 4 groups: sample_text, image_data, config_data, large_content
            assert len(duplicates) == 4
            
            # Check that each group has the expected number of files
            for (size, hash_val), paths in duplicates.items():
                assert len(paths) >= 2  # Each group should have at least 2 files

    def test_mock_args(self):
        """Test that MockArgs works correctly."""
        args = MockArgs()
        assert args.loglevel == "info"
        assert args.logfile is None

    def test_demo_integration(self):
        """Test the complete demo workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            
            # Create demo files
            file_mapping = create_demo_files(base_dir)
            
            # Set up logger
            args = MockArgs()
            logger = setup_logger(args)
            
            # Run scan
            duplicates = run_demo_scan(str(base_dir), logger)
            
            # Test results printing (should not raise exceptions)
            print_demo_results(duplicates, file_mapping, logger)
            
            # Verify that the demo found the expected results
            assert len(duplicates) == 4
            total_files = sum(len(paths) for paths in duplicates.values())
            assert total_files == 9  # 3+2+2+2 = 9 total duplicate files

    def test_demo_file_contents(self):
        """Test that demo files have the expected content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            file_mapping = create_demo_files(base_dir)
            
            # Check that duplicate files have identical content
            sample_text_files = file_mapping["sample_text"]
            first_content = Path(sample_text_files[0]).read_text()
            
            for file_path in sample_text_files[1:]:
                assert Path(file_path).read_text() == first_content
            
            # Check that image files have identical content
            image_files = file_mapping["image_data"]
            first_image_content = Path(image_files[0]).read_bytes()
            
            for file_path in image_files[1:]:
                assert Path(file_path).read_bytes() == first_image_content

    def test_demo_cli_integration(self):
        """Test that demo works correctly from CLI."""
        # Test that demo runs without errors
        result = subprocess.run([
            sys.executable, "-m", "duplicatemaster", "--demo"
        ], capture_output=True, text=True)
        
        # Should exit successfully
        assert result.returncode == 0
        
        # Should contain demo output
        assert "DEMO RESULTS" in result.stdout
        assert "Found 4 duplicate groups" in result.stdout 