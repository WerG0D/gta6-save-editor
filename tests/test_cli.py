import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from gta6_save import BLOCK, main


class CliTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.a = Path(folder.name) / "a"
        self.b = Path(folder.name) / "b"

    def invoke(self, *args):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(main(list(map(str, args))), 0)
        return [json.loads(line) for line in stream.getvalue().splitlines()]

    def test_inspect(self):
        self.a.write_bytes(b"abc")
        self.assertEqual(self.invoke("inspect", self.a), [
            {"file": "a", "bytes": 3, "sha256": hashlib.sha256(b"abc").hexdigest()}
        ])

    def test_diff(self):
        for a, b, expected in [
            (b"", b"", []), (b"a", b"a", []), (b"", b"abc", [(0, 3)]),
            (b"abc", b"a", [(1, 3)]), (b"abc", b"xbd", [(0, 1), (2, 3)]),
            (b"a" * (BLOCK - 1) + b"xxa", b"a" * (BLOCK - 1) + b"yya", [(BLOCK - 1, BLOCK + 1)]),
        ]:
            with self.subTest(expected=expected):
                self.a.write_bytes(a)
                self.b.write_bytes(b)
                rows = self.invoke("diff", self.a, self.b)
                self.assertEqual([(r["start"], r["end_exclusive"]) for r in rows], expected)
                self.assertEqual(self.a.read_bytes(), a)
                self.assertEqual(self.b.read_bytes(), b)

    def test_missing(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["inspect", str(self.a)]), 1)
