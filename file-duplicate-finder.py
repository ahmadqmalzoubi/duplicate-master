#!/usr/bin/env python3

import os
import hashlib
import argparse


def get_files_recursively(baseDir):
    for dentry in os.scandir(baseDir):
        if dentry.name.startswith('.') or dentry.is_symlink():
            continue
        elif dentry.is_dir(follow_symlinks=False):
            yield from get_files_recursively(dentry.path)
        else:
            yield dentry


def blake2bsum(filename, buffer_size=4096):
    sum = hashlib.blake2b()
    with open(filename, 'rb') as f:
        data = f.read(buffer_size)
        sum.update(data)
    return sum.hexdigest()


def human_readable_size(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


parser = argparse.ArgumentParser(
    description='Find the duplicate files and store them in a python dictionary')
parser.add_argument('basedir', nargs='?', default=".",
                    help='path of the directory to search for file duplicates')
parser.add_argument('--minsize', nargs='?', default=4096, type=int,
                    help='minumum size in bytes of the files to be searched')
parser.add_argument('--maxsize', nargs='?', default=4294967296, type=int,
                    help='maximum size in bytes of the files to be searched')
args = parser.parse_args()


base_dir = os.path.abspath(args.basedir)
file_max_size = args.maxsize
file_min_size = args.minsize


first4khash_files_dict = {}

for file in get_files_recursively(base_dir):
    file_size = os.stat(file.path).st_size
    if file_size > 0 and file_min_size < file_size < file_max_size:
        file_first4khash = blake2bsum(file.path)
        first4khash_files_dict.setdefault(
            f'{file_size}-{file_first4khash}', list()).append(file.path)


wholefilehash_files_dict = {}

for sizehash, fileslist in first4khash_files_dict.items():
    if len(fileslist) > 1:
        file_size = int(sizehash.split('-')[0])
        for file in fileslist:
            whole_file_hash = blake2bsum(file, file_size)
            wholefilehash_files_dict.setdefault(
                f'{file_size}-{whole_file_hash}', list()).append(file)


unsorted_duplicate_files_dict = {sizehash: fileslist for sizehash,
                                 fileslist in wholefilehash_files_dict.items() if len(fileslist) > 1}

duplicate_files_dict = dict(sorted(unsorted_duplicate_files_dict.items()))


print("\n# Duplicates:\n")
print("File Size\tFiles Hash with the list of duplicate files\n")

number_of_groups = len(duplicate_files_dict.keys())
number_of_all_files = 0

for sizehash, fileslist in duplicate_files_dict.items():
    file_size = int(sizehash.split('-')[0])
    file_hash = sizehash.split('-')[1]
    print(human_readable_size(file_size))
    number_of_all_files += len(fileslist)
    print("\t", file_hash)
    print("\t", fileslist)
    print("")

number_of_duplicate_files = number_of_all_files - number_of_groups

print(
    f"\n## Searching for duplicate files in the Base Directory: {base_dir} ->\n")

print(
    f"There are {number_of_groups} groups of duplicate files with \
{number_of_all_files} total number of files in these groups, whereof \
{number_of_duplicate_files} are duplicates.\n")
