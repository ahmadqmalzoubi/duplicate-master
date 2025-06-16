def analyze_space_savings(duplicates):
    total = savings = 0
    for (size, _), paths in duplicates.items():
        total += size * len(paths)
        savings += size * (len(paths) - 1)
    return total, savings


def format_bytes(size):
    for unit in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
