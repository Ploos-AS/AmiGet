#!/usr/bin/env python3
"""AmiGet M2 host-side qualification gate."""

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "AmiGetIndex"
FIXTURE = ROOT / "tests/fixtures/aminet-index.sample"


def run(*args: str, expect: int = 0) -> str:
    proc = subprocess.run(
        [str(BIN), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != expect:
        print(proc.stdout, end="")
        raise SystemExit(
            f"M2 FAIL: {' '.join(args)} returned {proc.returncode}, expected {expect}"
        )
    return proc.stdout


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"M2 FAIL: {label} missing {needle!r}")


def main() -> int:
    required = [
        ROOT / "include/aminet_index.h",
        ROOT / "src/aminet_index.c",
        ROOT / "tools/aminet_index_main.c",
        ROOT / "tools/fetch_aminet_index.py",
        FIXTURE,
        ROOT / "docs/M2_AMINET_INDEX.md",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        raise SystemExit("M2 FAIL: missing files: " + ", ".join(missing))

    if not BIN.is_file():
        raise SystemExit("M2 FAIL: AmiGetIndex binary missing; run make first")

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = Path(tmpdir) / "aminet.cache"
        out = run("build", str(FIXTURE), str(cache))
        require(out, "indexed 4 Aminet entries", "build")

        cache_text = cache.read_text(encoding="utf-8")
        require(cache_text, "amiget.lha\tutil/cli\t34K", "cache")
        require(cache_text, "AmiSSL-5.19.lha\tutil/libs\t4M", "cache")

        out = run("search", str(cache), "ssl")
        require(out, "AmiSSL-5.19.lha", "case-insensitive search")

        out = run("search", str(cache), "TCP/IP")
        require(out, "RoadshowDemo.lha", "description search")

        out = run("search", str(cache), "definitely-not-present", expect=2)
        if out.strip():
            raise SystemExit("M2 FAIL: no-match search should be quiet")

    print("M2 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
