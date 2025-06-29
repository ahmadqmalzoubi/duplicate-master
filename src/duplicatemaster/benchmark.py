import time
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Any, Callable, Optional
from .deduper import find_duplicates
from .logger import setup_logger


class PerformanceBenchmark:
    """Performance benchmarking for duplicate file finder."""
    
    def __init__(self, logger: Any = None):
        self.logger = logger or setup_logger(type('Args', (), {'loglevel': 'info', 'logfile': None})())
        self.results = {}
    
    def create_test_data(self, base_dir: Path, num_files: int = 1000, num_duplicates: int = 100) -> Dict[str, Any]:
        """
        Create test data for benchmarking.
        
        Args:
            base_dir: Directory to create test files in
            num_files: Number of unique files to create
            num_duplicates: Number of duplicate files to create
            
        Returns:
            Dictionary with test data statistics
        """
        self.logger.info(f"Creating test data: {num_files} unique files, {num_duplicates} duplicates")
        
        # Create subdirectories
        subdirs = [base_dir / f"dir_{i}" for i in range(5)]
        for subdir in subdirs:
            subdir.mkdir(exist_ok=True)
        
        # Create unique files
        unique_files = []
        for i in range(num_files):
            subdir = subdirs[i % len(subdirs)]
            file_path = subdir / f"unique_{i}.txt"
            content = f"Unique file content {i} with some random data to make it different from others. " * 10
            file_path.write_text(content)
            unique_files.append(file_path)
        
        # Create duplicate files
        duplicate_files = []
        for i in range(num_duplicates):
            # Choose a random unique file to duplicate
            source_file = unique_files[i % len(unique_files)]
            subdir = subdirs[i % len(subdirs)]
            duplicate_path = subdir / f"duplicate_{i}.txt"
            shutil.copy2(source_file, duplicate_path)
            duplicate_files.append(duplicate_path)
        
        total_files = len(unique_files) + len(duplicate_files)
        total_size = sum(f.stat().st_size for f in unique_files + duplicate_files)
        
        stats = {
            'unique_files': len(unique_files),
            'duplicate_files': len(duplicate_files),
            'total_files': total_files,
            'total_size': total_size,
            'subdirectories': len(subdirs)
        }
        
        self.logger.info(f"Test data created: {stats}")
        return stats
    
    def benchmark_scan(self, 
                      base_dir: str, 
                      scan_name: str,
                      use_optimized: bool = True,
                      threads: int = 4,
                      quick_mode: bool = True) -> Dict[str, Any]:
        """
        Benchmark a single scan operation.
        
        Args:
            base_dir: Directory to scan
            scan_name: Name for this benchmark
            use_optimized: Use optimized scanning
            threads: Number of threads
            quick_mode: Use quick scan mode
            
        Returns:
            Dictionary with benchmark results
        """
        self.logger.info(f"Starting benchmark: {scan_name}")
        
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        duplicates = find_duplicates(
            base_dir=base_dir,
            min_size=0,
            max_size=1024 * 1024 * 1024,  # 1GB
            quick_mode=quick_mode,
            multi_region=False,
            exclude=[],
            exclude_dir=[],
            exclude_hidden=False,
            threads=threads,
            logger=self.logger,
            use_optimized_scanning=use_optimized
        )
        
        end_time = time.time()
        end_memory = self._get_memory_usage()
        
        duration = end_time - start_time
        memory_used = end_memory - start_memory
        
        result = {
            'scan_name': scan_name,
            'duration': duration,
            'memory_used': memory_used,
            'duplicates_found': len(duplicates),
            'total_duplicate_files': sum(len(paths) for paths in duplicates.values()),
            'use_optimized': use_optimized,
            'threads': threads,
            'quick_mode': quick_mode
        }
        
        self.logger.info(f"Benchmark {scan_name} completed in {duration:.2f}s")
        self.logger.info(f"  - Duplicates found: {len(duplicates)} groups")
        self.logger.info(f"  - Memory used: {memory_used:.1f} MB")
        
        return result
    
    def run_comprehensive_benchmark(self, test_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Run a comprehensive benchmark comparing different configurations.
        
        Args:
            test_dir: Directory to use for testing (None for temporary directory)
            
        Returns:
            Dictionary with all benchmark results
        """
        if test_dir is None:
            with tempfile.TemporaryDirectory() as temp_dir:
                return self._run_benchmark_in_dir(Path(temp_dir))
        else:
            return self._run_benchmark_in_dir(Path(test_dir))
    
    def _run_benchmark_in_dir(self, base_dir: Path) -> Dict[str, Any]:
        """Run benchmarks in the specified directory."""
        # Create test data
        test_stats = self.create_test_data(base_dir, num_files=500, num_duplicates=50)
        
        # Define benchmark configurations
        configs = [
            {'name': 'Optimized Quick (4 threads)', 'optimized': True, 'threads': 4, 'quick': True},
            {'name': 'Optimized Quick (8 threads)', 'optimized': True, 'threads': 8, 'quick': True},
            {'name': 'Optimized Full (4 threads)', 'optimized': True, 'threads': 4, 'quick': False},
            {'name': 'Legacy Quick (4 threads)', 'optimized': False, 'threads': 4, 'quick': True},
            {'name': 'Legacy Full (4 threads)', 'optimized': False, 'threads': 4, 'quick': False},
        ]
        
        results = []
        for config in configs:
            result = self.benchmark_scan(
                base_dir=str(base_dir),
                scan_name=config['name'],
                use_optimized=config['optimized'],
                threads=config['threads'],
                quick_mode=config['quick']
            )
            results.append(result)
        
        # Calculate performance improvements
        baseline = next(r for r in results if not r['use_optimized'] and r['quick_mode'])
        improvements = []
        
        for result in results:
            if result != baseline:
                speedup = baseline['duration'] / result['duration']
                
                # Handle division by zero for memory improvement
                if baseline['memory_used'] > 0:
                    memory_improvement = (baseline['memory_used'] - result['memory_used']) / baseline['memory_used'] * 100
                else:
                    memory_improvement = 0.0  # No baseline memory to compare against
                
                improvements.append({
                    'scan_name': result['scan_name'],
                    'speedup': speedup,
                    'memory_improvement': memory_improvement,
                    'baseline_duration': baseline['duration'],
                    'optimized_duration': result['duration']
                })
        
        return {
            'test_stats': test_stats,
            'results': results,
            'improvements': improvements,
            'baseline': baseline
        }
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return 0.0  # psutil not available
    
    def print_results(self, benchmark_results: Dict[str, Any]) -> None:
        """Print formatted benchmark results."""
        print("\n" + "="*80)
        print("🚀 PERFORMANCE BENCHMARK RESULTS")
        print("="*80)
        
        # Test data summary
        stats = benchmark_results['test_stats']
        print(f"\n📊 Test Data:")
        print(f"   • {stats['unique_files']} unique files")
        print(f"   • {stats['duplicate_files']} duplicate files")
        print(f"   • {stats['total_files']} total files")
        print(f"   • {stats['total_size'] / 1024 / 1024:.1f} MB total size")
        print(f"   • {stats['subdirectories']} subdirectories")
        
        # Results table
        print(f"\n⏱️  Scan Performance:")
        print(f"{'Scan Method':<30} {'Duration (s)':<12} {'Memory (MB)':<12} {'Duplicates':<10}")
        print("-" * 70)
        
        for result in benchmark_results['results']:
            print(f"{result['scan_name']:<30} {result['duration']:<12.2f} {result['memory_used']:<12.1f} {result['duplicates_found']:<10}")
        
        # Performance improvements
        if benchmark_results['improvements']:
            print(f"\n📈 Performance Improvements (vs Legacy Quick):")
            print(f"{'Scan Method':<30} {'Speedup':<10} {'Memory Saved':<15}")
            print("-" * 60)
            
            for improvement in benchmark_results['improvements']:
                speedup_str = f"{improvement['speedup']:.1f}x"
                memory_str = f"{improvement['memory_improvement']:.1f}%"
                print(f"{improvement['scan_name']:<30} {speedup_str:<10} {memory_str:<15}")
        
        print("\n" + "="*80)


def run_benchmark(test_dir: Optional[str] = None) -> None:
    """
    Run a performance benchmark and display results.
    
    Args:
        test_dir: Directory to use for testing (None for temporary directory)
    """
    benchmark = PerformanceBenchmark()
    results = benchmark.run_comprehensive_benchmark(test_dir)
    benchmark.print_results(results) 