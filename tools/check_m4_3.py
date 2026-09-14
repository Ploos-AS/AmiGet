#!/usr/bin/env python3
"""AmiGet M4.3 host-side qualification gate."""

from __future__ import annotations

import struct
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EXTRACT = ROOT / "tools/extract_lha_staging.py"
DOC = ROOT / "docs/M4_3_STAGING_EXTRACTION.md"


def make_member(name: str, payload: bytes, method: bytes = b"-lh0-") -> bytes:
    name_b = name.encode("latin-1")
    header_size = 22 + len(name_b)
    header = bytearray(header_size + 2)
    header[0] = header_size
    header[1] = 0
    header[2:7] = method
    struct.pack_into("<I", header, 7, len(payload))
    struct.pack_into("<I", header, 11, len(payload))
    struct.pack_into("<I", header, 15, 0)
    header[19] = 0x20
    header[20] = 0
    header[21] = len(name_b)
    header[22:22 + len(name_b)] = name_b
    header[22 + len(name_b):24 + len(name_b)] = b"\x00\x00"
    return bytes(header) + payload


def run(*args: str, expect: int = 0) -> str:
    proc = subprocess.run(
        [sys.executable, str(EXTRACT), *args], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if proc.returncode != expect:
        print(proc.stdout, end="")
        raise SystemExit(f"M4.3 FAIL: extractor returned {proc.returncode}, expected {expect}")
    return proc.stdout


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"M4.3 FAIL: {label} missing {needle!r}")


def main() -> int:
    for path in (EXTRACT, DOC):
        if not path.is_file():
            raise SystemExit(f"M4.3 FAIL: missing {path.relative_to(ROOT)}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        archive = tmp / "sample.lha"
        archive.write_bytes(
            make_member("C/sample", b"hello") +
            make_member("Libs/sample.library", b"library") +
            b"\x00"
        )
        staging = tmp / "stage"
        state = tmp / "extract.state"
        out = run("--archive", str(archive), "--staging", str(staging), "--state", str(state))
        require(out, "extracted 2 LhA members to staging", "success output")
        if (staging / "C/sample").read_bytes() != b"hello":
            raise SystemExit("M4.3 FAIL: C/sample payload mismatch")
        if (staging / "Libs/sample.library").read_bytes() != b"library":
            raise SystemExit("M4.3 FAIL: library payload mismatch")
        body = state.read_text(encoding="utf-8")
        require(body, "status=extracted-staging", "state")
        require(body, "extract_ready=yes", "extract gate")
        require(body, "install_ready=no", "install gate")

        # Existing staging destinations must never be overwritten.
        existing = tmp / "existing"
        existing.mkdir()
        sentinel = existing / "keep"
        sentinel.write_text("preserve", encoding="utf-8")
        out = run("--archive", str(archive), "--staging", str(existing),
                  "--state", str(tmp / "existing.state"), expect=1)
        require(out, "staging destination already exists", "overwrite refusal")
        if sentinel.read_text(encoding="utf-8") != "preserve":
            raise SystemExit("M4.3 FAIL: existing staging tree was modified")

        # Traversal paths are rejected before any staging tree is promoted.
        evil = tmp / "evil.lha"
        evil.write_bytes(make_member("../escape", b"bad") + b"\x00")
        evil_stage = tmp / "evil-stage"
        out = run("--archive", str(evil), "--staging", str(evil_stage),
                  "--state", str(tmp / "evil.state"), expect=1)
        require(out, "unsafe archive member path", "traversal refusal")
        if evil_stage.exists():
            raise SystemExit("M4.3 FAIL: failed extraction left promoted staging tree")

        # Compressed methods remain fail-closed until a decoder is qualified.
        compressed = tmp / "compressed.lha"
        compressed.write_bytes(make_member("C/test", b"x", b"-lh5-") + b"\x00")
        out = run("--archive", str(compressed), "--staging", str(tmp / "compressed-stage"),
                  "--state", str(tmp / "compressed.state"), expect=1)
        require(out, "does not support method: -lh5-", "unsupported compression refusal")

        # Duplicate member paths must fail rather than overwrite inside staging.
        duplicate = tmp / "duplicate.lha"
        duplicate.write_bytes(
            make_member("C/same", b"one") + make_member("C/same", b"two") + b"\x00"
        )
        duplicate_stage = tmp / "duplicate-stage"
        out = run("--archive", str(duplicate), "--staging", str(duplicate_stage),
                  "--state", str(tmp / "duplicate.state"), expect=1)
        require(out, "duplicate archive member path", "duplicate refusal")
        if duplicate_stage.exists():
            raise SystemExit("M4.3 FAIL: duplicate extraction left promoted staging tree")

    print("M4.3 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
