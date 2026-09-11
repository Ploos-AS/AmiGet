#!/usr/bin/env python3
"""AmiGet M2.2 host-side qualification gate."""

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "AmiGet"
FIXTURE = ROOT / "tests/fixtures/aminet-index.sample"


def run(*args: str, expect: int = 0) -> str:
    proc = subprocess.run(
        [str(BIN), *args], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if proc.returncode != expect:
        print(proc.stdout, end="")
        raise SystemExit(
            f"M2.2 FAIL: {' '.join(args)} returned {proc.returncode}, expected {expect}"
        )
    return proc.stdout


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"M2.2 FAIL: {label} missing {needle!r}")


def main() -> int:
    required = [
        ROOT / "config/mirrors.conf",
        ROOT / "tools/fetch_aminet_index.py",
        ROOT / "include/aminet_index.h",
        ROOT / "src/aminet_index.c",
        FIXTURE,
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        raise SystemExit("M2.2 FAIL: missing files: " + ", ".join(missing))

    out = run("version")
    require(out, "AmiGet ", "program identity")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        cache = tmp / "aminet.cache"

        out = run("update", str(FIXTURE), str(cache))
        require(out, "indexed 4 Aminet entries", "initial update")
        require(out, "cache updated", "initial update")
        original = cache.read_text(encoding="utf-8")
        require(original, "AmiSSL-5.19.lha", "cache contents")

        bad_index = tmp / "bad.INDEX"
        bad_index.write_text("this is not an Aminet index\n", encoding="utf-8")
        out = run("update", str(bad_index), str(cache), expect=1)
        require(out, "contained no usable entries", "invalid index rejection")
        if cache.read_text(encoding="utf-8") != original:
            raise SystemExit("M2.2 FAIL: failed update changed existing cache")
        if (tmp / "aminet.cache.new").exists():
            raise SystemExit("M2.2 FAIL: failed update left temporary cache")

    mirrors = (ROOT / "config/mirrors.conf").read_text(encoding="utf-8")
    if mirrors.count("https://") < 2:
        raise SystemExit("M2.2 FAIL: mirror config should contain fallback mirrors")

    print("M2.2 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
