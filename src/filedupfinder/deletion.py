import os
import logging
from typing import List, Dict, Tuple, Any

logger = logging.getLogger(__name__)


def delete_files(files_to_delete: List[str], dry_run: bool, logger_obj: logging.Logger = logger):
    """
    Deletes a list of files, with an option for a dry run.

    Args:
        files_to_delete: A list of file paths to be deleted.
        dry_run: If True, only log the files that would be deleted without actually deleting them.
        logger_obj: The logger to use for output.
    """
    for path in files_to_delete:
        if dry_run:
            logger_obj.info(f"[DRY-RUN] Would delete: {path}")
        else:
            try:
                os.remove(path)
                logger_obj.info(f"Deleted: {path}")
            except Exception as e:
                logger_obj.error(f"Failed to delete {path}: {e}")


def handle_deletion(duplicates: Dict[Tuple[int, str], List[str]], args: Any, logger_obj: logging.Logger = logger):
    """
    Handles the interactive or automatic deletion of duplicate files based on command-line arguments.

    Args:
        duplicates: A dictionary of duplicate files.
        args: Command-line arguments.
        logger_obj: The logger to use for output.
    """
    if not args.force and not args.dry_run:
        confirm = input("Confirm deletion? (y/N): ").strip().lower()
        if confirm != 'y':
            logger_obj.info("Deletion cancelled.")
            return

    for (size, hash_val), paths in sorted(duplicates.items()):
        if len(paths) < 2:
            continue

        to_delete: List[str] = []
        if args.interactive:
            print(
                f"\nDuplicate group (Size: {size}, Hash: {hash_val[:8]}...):")
            for i, p in enumerate(paths):
                print(f"  [{i}] {p}")
            choice = input(
                "Enter file indices to delete (comma-separated), 'a' for all but first, or 's' to skip: ").strip().lower()

            if choice == 's':
                continue
            elif choice == 'a':
                to_delete = paths[1:]
            else:
                try:
                    indices = [int(i.strip()) for i in choice.split(',')]
                    to_delete = [paths[i]
                                 for i in indices if 0 <= i < len(paths)]
                except ValueError:
                    logger_obj.warning(f"Invalid input: {choice}. Skipping group.")
                    continue
        else:
            to_delete = paths[1:]

        if to_delete:
            delete_files(to_delete, args.dry_run, logger_obj)

