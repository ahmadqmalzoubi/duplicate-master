import os

def handle_deletion(duplicates, args, logger):
    if not args.force:
        confirm = input("Confirm deletion? (y/N): ").strip().lower()
        if confirm != 'y':
            logger.info("Deletion cancelled.")
            return

    for (size, hash), paths in sorted(duplicates.items()):
        if args.interactive:
            print(f"\nDuplicate group (Size: {size}, Hash: {hash[:8]}):")
            for i, p in enumerate(paths):
                print(f"  [{i}] {p}")
            choice = input("Delete files (comma-separated), 'a' for all but first, 's' to skip: ").strip().lower()
            if choice == 's':
                continue
            elif choice == 'a':
                to_delete = paths[1:]
            else:
                try:
                    to_delete = [paths[int(i)] for i in choice.split(',')]
                except:
                    continue
        else:
            to_delete = paths[1:]

        for path in to_delete:
            if args.dry_run:
                logger.info(f"[DRY-RUN] Would delete: {path}")
            else:
                try:
                    os.remove(path)
                    logger.info(f"Deleted: {path}")
                except Exception as e:
                    logger.error(f"Failed to delete {path}: {e}")

