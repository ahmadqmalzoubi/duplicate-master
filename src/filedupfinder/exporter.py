import json
import csv


def export_results(duplicates, args, logger):
    data = [{"size_bytes": size, "hash": hash, "paths": paths}
            for (size, hash), paths in duplicates.items()]

    if args.json_out:
        try:
            with open(args.json_out, 'w') as jf:
                json.dump(data, jf, indent=2)
            logger.info(f"Written to JSON: {args.json_out}")
        except Exception as e:
            logger.error(f"JSON export failed: {e}")

    if args.csv_out:
        try:
            with open(args.csv_out, 'w', newline='') as cf:
                writer = csv.DictWriter(
                    cf, fieldnames=["size_bytes", "hash", "path"])
                writer.writeheader()
                for row in data:
                    for path in row['paths']:
                        writer.writerow(
                            {"size_bytes": row['size_bytes'], "hash": row['hash'], "path": path})
            logger.info(f"Written to CSV: {args.csv_out}")
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
