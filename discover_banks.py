#!/usr/bin/env python3
"""
DAFNE — bank discovery CLI.

Usage:
    python3 discover_banks.py --base <dir>

Prints {"banks": [...]} to stdout: the union of every mounted grove's
declared `banks:` under <dir>, each bank's `bank:` path resolved to an
absolute path. Dafne answers a query here; it never writes a file, and it
does not know what a bank is for — see manifest.py's discover_grove_banks.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from manifest import discover_grove_banks  # noqa: E402


def parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    return p.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    banks = discover_grove_banks(Path(args.base))
    print(json.dumps({"banks": banks}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
