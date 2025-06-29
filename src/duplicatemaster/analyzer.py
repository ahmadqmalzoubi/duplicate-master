from typing import Dict, List, Tuple


def analyze_space_savings(duplicates: Dict[Tuple[int, str], List[str]]) -> Tuple[int, int]:
    """
    Analyze the disk space usage and potential savings from duplicate files.

    This function calculates the total disk space used by duplicate files and
    estimates how much space could be reclaimed by removing duplicates while
    keeping one copy of each file.

    Args:
        duplicates: A dictionary mapping (file_size, file_hash) tuples to lists
                   of file paths that are duplicates of each other.

    Returns:
        Tuple[int, int]: A tuple containing:
            - total_space: Total bytes used by all duplicate files
            - savings: Bytes that could be reclaimed by removing duplicates

    Examples:
        >>> duplicates = {(1024, 'abc123'): ['/path/file1.txt', '/path/file2.txt']}
        >>> total, savings = analyze_space_savings(duplicates)
        >>> print(f"Total: {total}, Savings: {savings}")
        Total: 2048, Savings: 1024
    """
    total = savings = 0
    for (size, _), paths in duplicates.items():
        total += size * len(paths)
        savings += size * (len(paths) - 1)
    return total, savings


def format_bytes(size: float) -> str:
    """
    Convert a file size in bytes to a human-readable string.

    This function converts byte values to the most appropriate unit (bytes, KB, MB, GB, TB)
    and formats the result with one decimal place.

    Args:
        size: File size in bytes.

    Returns:
        str: Human-readable file size string with appropriate unit.

    Examples:
        >>> format_bytes(1024)
        '1.0 KB'
        >>> format_bytes(1048576)
        '1.0 MB'
        >>> format_bytes(1073741824)
        '1.0 GB'
    """
    for unit in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
