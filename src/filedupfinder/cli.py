import argparse
from .hasher import DEFAULT_THREADS


def parse_args():
    parser = argparse.ArgumentParser(
        description="Parallel duplicate file finder")
    parser.add_argument('basedir', nargs='?', default=".",
                        help='Directory to scan')
    parser.add_argument('--minsize', type=int, default=4096)
    parser.add_argument('--maxsize', type=int, default=4294967296)
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
    return parser.parse_args()
