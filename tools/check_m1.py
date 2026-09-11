#!/usr/bin/env python3
"""AmiGet M1 host-side qualification gate."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "AmiGet"


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
            f"M1 FAIL: {' '.join(args)} returned {proc.returncode}, expected {expect}"
        )
    return proc.stdout


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"M1 FAIL: {label} missing {needle!r}")


def main() -> int:
    required = [
        ROOT / "Makefile",
        ROOT / "include/amiget.h",
        ROOT / "src/amiget.c",
        ROOT / "packages/catalogue.lst",
        ROOT / "packages/example.pkg",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        raise SystemExit("M1 FAIL: missing files: " + ", ".join(missing))

    if not BIN.is_file():
        raise SystemExit("M1 FAIL: AmiGet binary missing; run make first")

    out = run("version")
    require(out, "AmiGet 0.1.0-m1", "version")

    out = run("list")
    require(out, "example", "list")
    require(out, "M0 example package; not installable", "list")

    out = run("search", "EXAMPLE")
    require(out, "example", "case-insensitive search")

    out = run("info", "example")
    for needle in (
        "Name:           example",
        "Source:         aminet",
        "Minimum OS:     2.04",
        "Minimum CPU:    68000",
        "Install recipe: manual",
    ):
        require(out, needle, "info")

    out = run("search", "definitely-not-present", expect=2)
    if out.strip():
        raise SystemExit("M1 FAIL: no-match search should be quiet")

    out = run("info", "definitely-not-present", expect=2)
    require(out, "package not found", "missing package")

    print("M1 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
