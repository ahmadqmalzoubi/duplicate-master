import argparse
from .hasher import DEFAULT_THREADS


def parse_args():
    parser = argparse.ArgumentParser(
        description="Parallel duplicate file finder")
    parser.add_argument('basedir', nargs='?', default=".",
                        help='Directory to scan')
    parser.add_argument('--minsize', type=int, default=4,
                        help='Minimum file size in MB (default: 4 MB)')
    parser.add_argument('--maxsize', type=int, default=4096,
                        help='Maximum file size in MB (default: 4096 MB = 4 GB)')
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--multi-region', action='store_true')
    parser.add_argument('--threads', type=int, default=DEFAULT_THREADS)
    parser.add_argument('--loglevel', default="info",
                        choices=["debug", "info", "warning", "error"])
    parser.add_argument('--logfile', type=str)
    parser.add_argument('--json-out', type=str)
    parser.add_argument('--csv-out', type=str)
    parser.add_argument('--delete', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--interactive', action='store_true')
    parser.add_argument('--exclude', action='append', default=[])
    parser.add_argument('--exclude-dir', action='append', default=[])
    parser.add_argument('--exclude-hidden', action='store_true')
    
    args = parser.parse_args()
    
    # Convert MB to bytes for backward compatibility
    args.minsize = args.minsize * 1024 * 1024
    args.maxsize = args.maxsize * 1024 * 1024
    
    return args
