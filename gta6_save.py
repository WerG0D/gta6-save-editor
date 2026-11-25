"""Read-only binary inspection tools for save research."""
import argparse
import json
import mmap
import os
import stat
import sys
from contextlib import ExitStack
from pathlib import Path

from save_capture import BLOCK, capture, inspect_file, victory_manifest


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


def slot_inventory(root):
    """Hash regular files by relative path without following links inside a slot."""
    files = {}
    pending = [root]
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                info = entry.stat(follow_symlinks=False)
                if getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                    continue
                path = Path(entry.path)
                if stat.S_ISDIR(info.st_mode):
                    pending.append(path)
                elif stat.S_ISREG(info.st_mode):
                    record = inspect_file(path)
                    files[path.relative_to(root).as_posix()] = {
                        "bytes": record["bytes"], "sha256": record["sha256"]
                    }
    return files


def compare_slots(before, after):
    left = slot_inventory(before)
    right = slot_inventory(after)
    for path in sorted(left.keys() | right.keys()):
        if left.get(path) == right.get(path):
            continue
        if path not in left:
            change = "added"
        elif path not in right:
            change = "removed"
        else:
            change = "modified"
        yield {"path": path, "change": change, "before": left.get(path), "after": right.get(path)}


def find_integer(samples, width, byteorder, predict):
    """Yield fixed offsets matching every observed unsigned integer."""
    values = [int(value) for _, value in samples]
    if len(set(values)) < 2:
        raise ValueError("Provide at least two distinct observed values")
    if any(value < 0 or value >= 1 << (8 * width) for value in values):
        raise ValueError(f"Observed value outside the unsigned {width}-byte range")
    patterns = [value.to_bytes(width, byteorder) for value in values]
    with ExitStack() as stack:
        views = []
        for path, _ in samples:
            stream = stack.enter_context(open(path, "rb"))
            if os.fstat(stream.fileno()).st_size:
                views.append(stack.enter_context(mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ)))
            else:
                views.append(b"")
        reserved = stack.enter_context(predict.open("rb")) if predict else None
        end = min(map(len, views))
        offset = views[0].find(patterns[0], 0, end)
        while offset >= 0:
            if all(view[offset:offset + width] == pattern for view, pattern in zip(views[1:], patterns[1:])):
                row = {"offset": offset, "width": width, "byteorder": byteorder}
                if reserved:
                    reserved.seek(offset)
                    field = reserved.read(width)
                    row["prediction"] = int.from_bytes(field, byteorder) if len(field) == width else None
                yield row
            offset = views[0].find(patterns[0], offset + 1, end)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Print filename, size and SHA-256 as JSON")
    inspect.add_argument("file", type=Path)
    diff = commands.add_parser("diff", help="Print one JSON object per changed byte range")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    compare = commands.add_parser("compare-slots", help="List changed files between two saved slot directories")
    compare.add_argument("before", type=Path)
    compare.add_argument("after", type=Path)
    manifest = commands.add_parser("victory-manifest", help="Map logical blob names to numbered files in one VIctory manifest")
    manifest.add_argument("file", type=Path)
    snapshot = commands.add_parser("capture", help="Report VIctory versions and logical blob hashes from an offline copy")
    snapshot.add_argument("directory", type=Path)
    snapshot.add_argument("--commit", required=True, help="VIctory build commit recorded by the tester")
    snapshot.add_argument("--previous", type=Path, help="Earlier offline copy with the same directory layout")
    search = commands.add_parser("find-integer", help="Find fixed offsets matching observed unsigned integers")
    search.add_argument("--sample", nargs=2, action="append", required=True, metavar=("FILE", "VALUE"))
    search.add_argument("--width", type=int, choices=(1, 2, 4, 8), default=4, help="Integer width in bytes (default: 4)")
    search.add_argument("--byteorder", choices=("little", "big"), default="little")
    search.add_argument("--predict", type=Path, metavar="HELD_OUT_FILE")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            print(json.dumps(inspect_file(args.file)))
        elif args.command == "compare-slots":
            for change in compare_slots(args.before, args.after):
                print(json.dumps(change))
        elif args.command == "victory-manifest":
            print(json.dumps(victory_manifest(args.file)))
        elif args.command == "capture":
            print(json.dumps(capture(args.directory, args.commit, args.previous), indent=2, sort_keys=True))
        elif args.command == "find-integer":
            for row in find_integer(args.sample, args.width, args.byteorder, args.predict):
                print(json.dumps(row))
        else:
            for start, end in changed_ranges(args.before, args.after):
                print(json.dumps({"start": start, "end_exclusive": end}))
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
