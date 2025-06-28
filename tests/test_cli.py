import sys
from unittest.mock import patch
import pytest
import argparse
from duplicatemaster.cli import parse_args


def test_cli_defaults():
    test_argv = ["prog"]
    with patch.object(sys, "argv", test_argv):
        args = parse_args()
        assert args.basedir == "."
        assert args.minsize == 4 * 1024 * 1024
        assert args.maxsize == 4096 * 1024 * 1024
        assert args.quick is False
        assert args.multi_region is False
        assert args.loglevel == "info"
        assert args.logfile is None
        assert args.json_out is None
        assert args.csv_out is None
        assert args.delete is False
        assert args.dry_run is False
        assert args.force is False
        assert args.interactive is False
        assert args.exclude == []
        assert args.exclude_dir == []
        assert args.exclude_hidden is False


def test_cli_all_options():
    test_argv = [
        "prog", "/tmp/testdir",
        "--minsize", "10",
        "--maxsize", "100",
        "--quick",
        "--multi-region",
        "--threads", "8",
        "--loglevel", "debug",
        "--logfile", "log.txt",
        "--json-out", "out.json",
        "--csv-out", "out.csv",
        "--delete",
        "--dry-run",
        "--force",
        "--interactive",
        "--exclude", "*.tmp",
        "--exclude", "*.bak",
        "--exclude-dir", "venv",
        "--exclude-dir", "__pycache__",
        "--exclude-hidden"
    ]
    with patch.object(sys, "argv", test_argv):
        args = parse_args()
        assert args.basedir == "/tmp/testdir"
        assert args.minsize == 10 * 1024 * 1024
        assert args.maxsize == 100 * 1024 * 1024
        assert args.quick is True
        assert args.multi_region is True
        assert args.threads == 8
        assert args.loglevel == "debug"
        assert args.logfile == "log.txt"
        assert args.json_out == "out.json"
        assert args.csv_out == "out.csv"
        assert args.delete is True
        assert args.dry_run is True
        assert args.force is True
        assert args.interactive is True
        assert args.exclude == ["*.tmp", "*.bak"]
        assert args.exclude_dir == ["venv", "__pycache__"]
        assert args.exclude_hidden is True


def test_cli_minsize_maxsize_conversion():
    test_argv = ["prog", "--minsize", "1", "--maxsize", "2"]
    with patch.object(sys, "argv", test_argv):
        args = parse_args()
        assert args.minsize == 1 * 1024 * 1024
        assert args.maxsize == 2 * 1024 * 1024


def test_cli_exclude_multiple():
    test_argv = ["prog", "--exclude", "*.log", "--exclude", "*.tmp"]
    with patch.object(sys, "argv", test_argv):
        args = parse_args()
        assert args.exclude == ["*.log", "*.tmp"]


def test_cli_exclude_dir_multiple():
    test_argv = ["prog", "--exclude-dir", "venv", "--exclude-dir", "build"]
    with patch.object(sys, "argv", test_argv):
        args = parse_args()
        assert args.exclude_dir == ["venv", "build"]


def test_cli_boolean_flags():
    test_argv = ["prog", "--quick", "--delete", "--dry-run", "--force", "--interactive", "--exclude-hidden"]
    with patch.object(sys, "argv", test_argv):
        args = parse_args()
        assert args.quick is True
        assert args.delete is True
        assert args.dry_run is True
        assert args.force is True
        assert args.interactive is True
        assert args.exclude_hidden is True 