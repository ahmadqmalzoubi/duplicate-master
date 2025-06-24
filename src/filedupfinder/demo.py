import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Any
from .deduper import find_duplicates
from .analyzer import analyze_space_savings, format_bytes
from .logger import setup_logger


class MockArgs:
    """Mock arguments for demo mode."""
    def __init__(self):
        self.loglevel = "info"
        self.logfile = None


def create_demo_files(base_dir: Path) -> Dict[str, List[str]]:
    """
    Create demo files with known duplicates for testing.
    
    Args:
        base_dir: Directory to create demo files in
        
    Returns:
        Dictionary mapping file content to list of file paths
    """
    # Create subdirectories
    docs_dir = base_dir / "documents"
    pics_dir = base_dir / "pictures"
    backup_dir = base_dir / "backup"
    
    docs_dir.mkdir(exist_ok=True)
    pics_dir.mkdir(exist_ok=True)
    backup_dir.mkdir(exist_ok=True)
    
    # File contents that will create duplicates
    file_contents = {
        "sample_text": "This is a sample text file with some content that will be duplicated.\n" * 10,
        "image_data": b"Fake image data that represents a JPEG file. " * 100,
        "config_data": "config=value\nsetting=on\nmode=test\n" * 5,
        "large_content": "Large file content for testing. " * 1000,
    }
    
    # Create files with duplicates
    file_mapping = {}
    
    # Sample text files (3 duplicates)
    sample_text_files = [
        docs_dir / "report.txt",
        docs_dir / "report_copy.txt", 
        backup_dir / "report_backup.txt"
    ]
    for file_path in sample_text_files:
        file_path.write_text(file_contents["sample_text"])
    file_mapping["sample_text"] = [str(f) for f in sample_text_files]
    
    # Image files (2 duplicates)
    image_files = [
        pics_dir / "vacation.jpg",
        pics_dir / "vacation_copy.jpg"
    ]
    for file_path in image_files:
        file_path.write_bytes(file_contents["image_data"])
    file_mapping["image_data"] = [str(f) for f in image_files]
    
    # Config files (2 duplicates)
    config_files = [
        docs_dir / "settings.conf",
        backup_dir / "settings.conf"
    ]
    for file_path in config_files:
        file_path.write_text(file_contents["config_data"])
    file_mapping["config_data"] = [str(f) for f in config_files]
    
    # Large file (2 duplicates)
    large_files = [
        docs_dir / "large_document.txt",
        backup_dir / "large_document_backup.txt"
    ]
    for file_path in large_files:
        file_path.write_text(file_contents["large_content"])
    file_mapping["large_content"] = [str(f) for f in large_files]
    
    # Add some unique files
    unique_files = [
        docs_dir / "unique_note.txt",
        pics_dir / "unique_photo.png",
        backup_dir / "unique_backup.dat"
    ]
    
    unique_contents = [
        "This is a unique file that won't have duplicates.",
        b"Unique image data that's different from others.",
        "Unique backup data with different content."
    ]
    
    for file_path, content in zip(unique_files, unique_contents):
        if isinstance(content, str):
            file_path.write_text(content)
        else:
            file_path.write_bytes(content)
    
    return file_mapping


def run_demo_scan(base_dir: str, logger: Any) -> Dict[Tuple[int, str], List[str]]:
    """
    Run a demo scan on the created test files.
    
    Args:
        base_dir: Directory containing demo files
        logger: Logger instance
        
    Returns:
        Dictionary of duplicate files found
    """
    logger.info("🔍 Starting demo scan...")
    
    duplicates = find_duplicates(
        base_dir=base_dir,
        min_size=0,  # Include all file sizes for demo
        max_size=1024 * 1024 * 1024,  # 1GB max
        quick_mode=True,  # Use quick mode for faster demo
        multi_region=False,
        exclude=[],
        exclude_dir=[],
        exclude_hidden=False,
        threads=4,
        logger=logger
    )
    
    return duplicates


def print_demo_results(duplicates: Dict[Tuple[int, str], List[str]], 
                      file_mapping: Dict[str, List[str]], 
                      logger: Any) -> None:
    """
    Print demo results in a user-friendly format.
    
    Args:
        duplicates: Duplicate files found
        file_mapping: Original file mapping for comparison
        logger: Logger instance
    """
    total_space, savings = analyze_space_savings(duplicates)
    num_groups = len(duplicates)
    num_files = sum(len(paths) for paths in duplicates.values())
    
    logger.info("\n" + "="*60)
    logger.info("🎯 DEMO RESULTS")
    logger.info("="*60)
    logger.info(f"📊 Found {num_groups} duplicate groups")
    logger.info(f"📁 Total duplicate files: {num_files}")
    logger.info(f"💾 Space used by duplicates: {format_bytes(total_space)}")
    logger.info(f"🗑️  Space that can be reclaimed: {format_bytes(savings)}")
    logger.info("="*60)
    
    if num_groups == 0:
        logger.info("❌ No duplicate files found in demo data.")
        return
    
    logger.info("\n📋 Duplicate Groups Found:")
    logger.info("-" * 40)
    
    for i, ((size, hash_val), paths) in enumerate(duplicates.items(), 1):
        logger.info(f"\n🔍 Group {i} (Size: {format_bytes(size)}, Hash: {hash_val[:8]}...)")
        for j, path in enumerate(paths):
            # Show relative path for cleaner output
            rel_path = os.path.relpath(path)
            logger.info(f"  [{j}] {rel_path}")
    
    logger.info("\n✅ Demo completed successfully!")
    logger.info("💡 This demonstrates how the tool identifies and groups duplicate files.")


def cleanup_demo_files(base_dir: str, logger: Any) -> None:
    """
    Clean up demo files and directories.
    
    Args:
        base_dir: Directory to clean up
        logger: Logger instance
    """
    try:
        shutil.rmtree(base_dir)
        logger.info(f"🧹 Cleaned up demo directory: {base_dir}")
    except Exception as e:
        logger.warning(f"⚠️  Could not clean up demo directory: {e}")


def run_demo() -> None:
    """
    Run the complete demo: create files, scan, show results, cleanup.
    """
    # Set up logger
    args = MockArgs()
    logger = setup_logger(args)
    
    logger.info("🎬 Starting File Duplicate Finder Demo")
    logger.info("=" * 50)
    
    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir) / "demo_files"
        base_dir.mkdir()
        
        try:
            # Create demo files
            logger.info("📁 Creating demo files with duplicates...")
            file_mapping = create_demo_files(base_dir)
            
            # Run scan
            duplicates = run_demo_scan(str(base_dir), logger)
            
            # Show results
            print_demo_results(duplicates, file_mapping, logger)
            
        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
            raise
        finally:
            # Cleanup happens automatically with tempfile.TemporaryDirectory()
            pass
    
    logger.info("\n🎉 Demo completed! Try running the tool on your own files:")
    logger.info("   python -m filedupfinder.cli /path/to/your/directory") 