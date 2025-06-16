from .cli import parse_args
from .logger import setup_logger
from .deduper import find_duplicates
from .analyzer import analyze_space_savings, format_bytes
from .deletion import handle_deletion
from .exporter import export_results
import os


def main():
    args = parse_args()
    logger = setup_logger(args)

    if not os.path.exists(args.basedir) or not os.path.isdir(args.basedir):
        logger.error(f"Invalid directory: {args.basedir}")
        return

    duplicates = find_duplicates(
        base_dir=os.path.abspath(args.basedir),
        min_size=args.minsize,
        max_size=args.maxsize,
        quick_mode=args.quick,
        multi_region=args.multi_region,
        exclude=args.exclude,
        exclude_dir=args.exclude_dir,
        exclude_hidden=args.exclude_hidden,
        threads=args.threads,
        logger=logger
    )

    total_space, savings = analyze_space_savings(duplicates)
    num_groups = len(duplicates)
    num_files = sum(len(paths) for paths in duplicates.values())

    logger.info("\n📊 Scan Summary:")
    logger.info(f"   • {num_groups} duplicate groups detected")
    logger.info(f"   • {num_files} duplicate files in total")
    logger.info(
        f"   • {format_bytes(total_space)} of space used by duplicates")
    logger.info(f"   • {format_bytes(savings)} can be reclaimed")

    if args.delete:
        handle_deletion(duplicates, args, logger)

    export_results(duplicates, args, logger)


if __name__ == "__main__":
    main()
