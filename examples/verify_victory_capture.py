"""Exercise capture against VIctory's actual save backend on Windows.

Pass a local VIctory Git checkout containing REVISION. Requires Rust/MSVC.
All fixture writes and the test-only Rust adapter live in a temporary copy.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


REVISION = "940d32f69b22265690a0b5a15d6ded572ba33baf"
CLI = Path(__file__).resolve().parents[1] / "gta6_save.py"
ADAPTER = """
    #[test]
    fn verify_offline_capture() {
        let root = PathBuf::from(std::env::var_os("CAPTURE_FIXTURE_ROOT").unwrap());
        match std::env::var("CAPTURE_FIXTURE_STEP").unwrap().as_str() {
            "write" => assert_eq!(update(&root, "sample", &[("balance", Some("2000")), ("marker", Some("dock"))]), S_OK),
            "change" => assert_eq!(update(&root, "sample", &[("balance", Some("1750"))]), S_OK),
            phase => {
                let value = match phase { "reopen_a" => "2000", "reopen_b" => "1750", _ => panic!("unknown phase") };
                let (_, blobs) = state(&root).unwrap();
                assert_eq!(blobs, vec![("balance".into(), value.into()), ("marker".into(), "dock".into())]);
            }
        }
    }
"""


def fingerprint(root):
    return {p.relative_to(root): (p.stat().st_mtime_ns, p.read_bytes() if p.is_file() else None)
            for p in root.rglob("*")}


def verify(checkout, work):
    source = work / "source"
    subprocess.run(["git", "clone", "--quiet", "--no-checkout", "--no-local", checkout.resolve().as_uri(), source], check=True)
    subprocess.run(["git", "-C", source, "checkout", "--quiet", "--detach", REVISION], check=True)
    module = source / "crates/victory-hle/src/modules/xgamesave.rs"
    code = module.read_text(encoding="utf-8")
    anchor = "    /// Run by the crash test in a child process;"
    if code.count(anchor) != 1:
        raise RuntimeError("Unexpected VIctory fixture adapter location")
    module.write_text(code.replace(anchor, ADAPTER + "\n" + anchor), encoding="utf-8")
    live = work / "live"
    live.mkdir()
    for phase in ("write", "reopen_a", "change", "reopen_b"):
        result = subprocess.run(
            ["cargo", "test", "--locked", "-p", "victory-hle", "--lib",
             "modules::xgamesave::tests::verify_offline_capture", "--", "--exact"],
            cwd=source, env={**os.environ, "CAPTURE_FIXTURE_ROOT": str(live), "CAPTURE_FIXTURE_STEP": phase},
            check=True, stdout=subprocess.PIPE, text=True)
        if "1 passed; 0 failed" not in result.stdout:
            raise RuntimeError(f"No passing Rust fixture test for {phase}")
        if phase.startswith("reopen_"):
            shutil.copytree(live, work / phase[-1])

    a, b = work / "a", work / "b"
    before = [fingerprint(a), fingerprint(b)]
    raw = subprocess.check_output([sys.executable, CLI, "capture", b, "--commit", REVISION, "--previous", a])
    report = json.loads(raw)
    changes = report["changes"]
    expected = hashlib.sha256(b"balance").hexdigest()
    if len(changes) != 1 or (changes[0]["blob"], changes[0]["change"]) != (expected, "modified"):
        raise RuntimeError(f"Unexpected logical changes: {changes}")
    container = report["containers"][changes[0]["container"]]
    newest = container["versions"][0]
    if container["latest_complete"] != "v2" or newest["blobs"][expected]["sha256"] != hashlib.sha256(b"1750").hexdigest():
        raise RuntimeError("Wrong version or balance content")
    if before != [fingerprint(a), fingerprint(b)]:
        raise RuntimeError("Capture changed a snapshot")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        verify(args.checkout, Path(directory))
