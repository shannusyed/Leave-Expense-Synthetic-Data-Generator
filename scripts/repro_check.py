#!/usr/bin/env python3
"""
repro_check.py – Reproducibility verification script.

Runs generate_data.py twice and compares SHA-256 checksums of every
output file.  If all checksums match, the generator is deterministic.
"""

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checksums() -> dict:
    return {
        f.name: sha256_file(f)
        for f in sorted(DATA_DIR.glob("*.csv"))
    }


def main() -> int:
    print("Run 1 …")
    subprocess.run([sys.executable, str(ROOT / "generate_data.py")],
                   cwd=str(ROOT), check=True, capture_output=True)
    run1 = checksums()

    print("Run 2 …")
    subprocess.run([sys.executable, str(ROOT / "generate_data.py")],
                   cwd=str(ROOT), check=True, capture_output=True)
    run2 = checksums()

    all_match = True
    for name in sorted(set(run1) | set(run2)):
        h1 = run1.get(name, "MISSING")
        h2 = run2.get(name, "MISSING")
        status = "✅" if h1 == h2 else "❌"
        if h1 != h2:
            all_match = False
        print(f"  {status}  {name}")
        if h1 != h2:
            print(f"       Run 1: {h1}")
            print(f"       Run 2: {h2}")

    if all_match:
        print("\n✅  All files match — generation is fully reproducible!")
        return 0
    else:
        print("\n❌  Mismatch detected — generation is NOT reproducible!")
        return 1


if __name__ == "__main__":
    sys.exit(main())

