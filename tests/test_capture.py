import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from gta6_save import main


def make_version(path, blobs):
    path.mkdir(parents=True)
    names = ["private slot", "private display", *blobs]
    fields = [s.encode("utf-8") for s in names]
    (path / "manifest").write_bytes(b"".join(len(s).to_bytes(4, "little") + s for s in fields))
    for i, content in enumerate(blobs.values()):
        if content is not None:
            (path / str(i)).write_bytes(content)


def run_capture(root, *extra):
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = main(["capture", str(root), "--commit", "940d32f", *map(str, extra)])
    if code:
        raise AssertionError(f"capture exited with {code}")
    return json.loads(stream.getvalue())


class CaptureTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_versions_and_changed_logical_names(self):
        a, b = self.root / "A", self.root / "B"
        slot = "private profile/private directory"
        make_version(a / slot / "v1", {"wallet": b"123", "empty": b"", "gone": b"x"})
        make_version(b / slot / "v2", {"empty": b"", "wallet": b"124", "new": b"y"})
        make_version(b / slot / "v10", {"wallet": None})
        make_version(b / slot / "v11.new", {"staged": b"secret"})
        broken = b / slot / "v3"
        broken.mkdir()
        (broken / "manifest").write_bytes(b"\xff")
        report = run_capture(b, "--previous", a)
        container, = report["containers"].values()
        self.assertEqual(container["latest_complete"], "v2")
        partial, malformed, complete = container["versions"]
        self.assertEqual([v["version"] for v in container["versions"]], ["v10", "v3", "v2"])
        self.assertEqual(next(iter(partial["blobs"].values()))["problem"], "missing")
        self.assertEqual(malformed["problem"], "manifest:malformed")
        self.assertEqual(complete["status"], "complete")
        changes = {c["blob"]: c["change"] for c in report["changes"]}
        expected = {hashlib.sha256(name).hexdigest(): op for name, op in
                    [(b"wallet", "modified"), (b"gone", "removed"), (b"new", "added")]}
        self.assertEqual(changes, expected)
        self.assertNotIn("private", json.dumps(report))
        self.assertNotIn("wallet", json.dumps(report))
        self.assertTrue((b / slot / "v11.new/0").is_file())

    def test_only_incomplete_versions_are_not_compared(self):
        a, b = self.root / "A", self.root / "B"
        make_version(a / "v1", {"a": b"ok"})
        make_version(b / "v1", {"a": None})
        (b / "v1/0").mkdir()
        report = run_capture(b, "--previous", a)
        container, = report["containers"].values()
        self.assertIsNone(container["latest_complete"])
        self.assertEqual(report["changes"][0]["change"], "not_comparable")

    def test_linked_blob_is_not_hashed(self):
        make_version(self.root / "v1", {"a": None})
        outside = self.root / "private-data"
        outside.write_bytes(b"private")
        try:
            (self.root / "v1/0").symlink_to(outside)
        except OSError as error:
            self.skipTest(f"Symlink creation unavailable: {error}")
        container, = run_capture(self.root)["containers"].values()
        blob, = container["versions"][0]["blobs"].values()
        self.assertEqual(blob, {"file": "0", "problem": "link"})
