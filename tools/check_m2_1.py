#!/usr/bin/env python3
"""AmiGet M2.1 host-side qualification gate."""

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
AMI = ROOT / "AmiGet"
IDX = ROOT / "AmiGetIndex"
FIXTURE = ROOT / "tests/fixtures/aminet-index.sample"


def run(binary: Path, *args: str, expect: int = 0) -> str:
    proc = subprocess.run(
        [str(binary), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != expect:
        print(proc.stdout, end="")
        raise SystemExit(
            f"M2.1 FAIL: {binary.name} {' '.join(args)} returned "
            f"{proc.returncode}, expected {expect}"
        )
    return proc.stdout


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"M2.1 FAIL: {label} missing {needle!r}")


def main() -> int:
    for path in (AMI, IDX, FIXTURE, ROOT / "tools/check_m2_1.py"):
        if not path.is_file():
            raise SystemExit(f"M2.1 FAIL: missing {path.relative_to(ROOT)}")

    out = run(AMI, "version")
    require(out, "AmiGet ", "version identity")

    # Backward-compatible curated lookup still works with no Aminet cache present.
    out = run(AMI, "search", "example")
    require(out, "[curated]", "curated source marker")
    require(out, "example", "curated search")

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = Path(tmpdir) / "aminet.cache"
        run(IDX, "build", str(FIXTURE), str(cache))

        # A term absent from curated metadata can still succeed from Aminet.
        out = run(AMI, "search", "AmiSSL", "--aminet", str(cache))
        require(out, "AmiSSL-5.19.lha", "Aminet result")

        # Curated matches and Aminet matches may coexist in the same invocation.
        out = run(AMI, "search", "amiget", "--aminet", str(cache))
        require(out, "amiget.lha", "combined Aminet result")

        # Explicitly requested missing cache is an error, not silent fallback.
        missing = Path(tmpdir) / "missing.cache"
        out = run(AMI, "search", "example", "--aminet", str(missing), expect=1)
        require(out, "cannot open Aminet cache", "explicit missing cache")

        out = run(AMI, "search", "definitely-not-present", "--aminet", str(cache), expect=2)
        if "definitely-not-present" in out:
            raise SystemExit("M2.1 FAIL: no-match output leaked search term")

    print("M2.1 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
