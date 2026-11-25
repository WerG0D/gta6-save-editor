"""Patch a fixed-width unsigned integer in a verified offline copy."""
import hashlib
import os
import re
import tempfile
from pathlib import Path

from save_capture import BLOCK, inspect_file


def patch_integer(source, output, sha256, offset, width, byteorder, expected, value):
    if not re.fullmatch(r"[0-9a-fA-F]{64}", sha256):
        raise ValueError("Expected a 64-digit SHA-256 digest")
    if offset < 0:
        raise ValueError("Offset must be nonnegative")
    if any(number < 0 or number >= 1 << (width * 8) for number in (expected, value)):
        raise ValueError(f"Value outside the unsigned {width}-byte range")

    original_hash = hashlib.sha256()
    patched_hash = hashlib.sha256()
    replacement = value.to_bytes(width, byteorder)
    with tempfile.TemporaryDirectory(prefix=".save-patch-", dir=output.parent) as directory:
        staged = Path(directory) / "output"
        with source.open("rb") as reader, staged.open("wb") as writer:
            remaining = offset
            while remaining:
                block = reader.read(min(BLOCK, remaining))
                if not block:
                    raise ValueError("Field extends beyond the input")
                original_hash.update(block)
                patched_hash.update(block)
                writer.write(block)
                remaining -= len(block)

            field = reader.read(width)
            if len(field) != width:
                raise ValueError("Field extends beyond the input")
            original_hash.update(field)
            patched_hash.update(replacement)
            writer.write(replacement)

            while block := reader.read(BLOCK):
                original_hash.update(block)
                patched_hash.update(block)
                writer.write(block)

        if original_hash.hexdigest() != sha256.lower():
            raise ValueError("Input SHA-256 does not match")
        if int.from_bytes(field, byteorder) != expected:
            raise ValueError("Expected integer does not match the input")

        result = inspect_file(staged)
        with staged.open("rb") as reader:
            reader.seek(offset)
            if reader.read(width) != replacement or result["sha256"] != patched_hash.hexdigest():
                raise OSError("Patched copy failed verification")
        # Publishing the verified file with a hard link cannot replace any
        # existing destination, even if another process creates it first.
        os.link(staged, output)

    return {**result, "file": output.name, "offset": offset, "width": width,
            "byteorder": byteorder, "old_value": expected, "new_value": value}
