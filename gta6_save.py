"""Read-only binary inspection tools for save research."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

BLOCK = 64 * 1024


def inspect_file(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while block := stream.read(BLOCK):
            size += len(block)
            digest.update(block)
    return {"file": path.name, "bytes": size, "sha256": digest.hexdigest()}


def changed_ranges(left, right):
    """Yield positional differences as half-open intervals, including any tail."""
    offset = 0
    start = None
    with left.open("rb") as a, right.open("rb") as b:
        while True:
            x, y = a.read(BLOCK), b.read(BLOCK)
            width = max(len(x), len(y))
            if not width:
                break
            if x == y:
                if start is not None:
                    yield start, offset
                    start = None
            else:
                for i in range(width):
                    different = i >= len(x) or i >= len(y) or x[i] != y[i]
                    if different and start is None:
                        start = offset + i
                    elif not different and start is not None:
                        yield start, offset + i
                        start = None
            offset += width
    if start is not None:
        yield start, offset


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Print filename, size and SHA-256 as JSON")
    inspect.add_argument("file", type=Path)
    diff = commands.add_parser("diff", help="Print one JSON object per changed byte range")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            print(json.dumps(inspect_file(args.file)))
        else:
            for start, end in changed_ranges(args.before, args.after):
                print(json.dumps({"start": start, "end_exclusive": end}))
    except OSError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
