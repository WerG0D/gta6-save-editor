"""Find, predict and patch a balance in synthetic offline snapshots."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


CLI = Path(__file__).resolve().parents[1] / "gta6_save.py"
# Each row is an independent fixture. The held-out observation is excluded
# from the search and checked only after the CLI returns its prediction.
FIXTURES = {
    "A":   "01 ab cd ef  d0 07 00 00  01 ab cd ef  d0 07 00 00",
    "A2":  "02 ab cd ef  d1 07 00 00  02 ab cd ef  d0 07 00 00",
    "B":   "03 ab cd ef  d6 06 00 00  03 ab cd ef  d6 06 00 00",
    "C":   "04 ab cd ef  d7 06 00 00  04 ab cd ef  dc 05 00 00",
    "D":   "05 ab cd ef  d8 06 00 00  05 ab cd ef  c3 05 00 00",
}


def main():
    with tempfile.TemporaryDirectory() as folder:
        for name, data in FIXTURES.items():
            (Path(folder) / name).write_bytes(bytes.fromhex(data))
        command = [sys.executable, str(CLI), "find-integer", "--sample", "A", "2000", "--sample", "B", "1750"]

        def search(args):
            output = subprocess.check_output(args, cwd=folder, text=True)
            return [json.loads(line) for line in output.splitlines()]

        initial = [row["offset"] for row in search(command)]
        print("Candidates from A and B:", initial)
        rows = search(command + ["--sample", "A2", "2000", "--sample", "C", "1500", "--predict", "D"])
        print("After controls, with held-out prediction:", json.dumps(rows))
        if initial != [4, 12] or rows != [{"offset": 12, "width": 4, "byteorder": "little", "prediction": 1475}]:
            raise SystemExit("Synthetic validation failed")
        print("Verified against the separate observation for D: 1475")
        source = Path(folder) / "D"
        original = source.read_bytes()
        result, = search([
            sys.executable, str(CLI), "patch-integer", "D", "D-edited",
            "--sha256", hashlib.sha256(original).hexdigest(), "--offset", "12",
            "--width", "4", "--byteorder", "little", "--expect", "1475", "--value", "1600",
        ])
        edited = (Path(folder) / "D-edited").read_bytes()
        if source.read_bytes() != original or edited != original[:12] + (1600).to_bytes(4, "little"):
            raise SystemExit("Synthetic edit verification failed")
        print("Verified edit in a separate copy:", json.dumps(result))


if __name__ == "__main__":
    main()
