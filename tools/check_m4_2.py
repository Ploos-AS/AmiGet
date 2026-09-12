#!/usr/bin/env python3
"""AmiGet M4.2 host-side qualification gate."""

from __future__ import annotations

import struct
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
INSPECT = ROOT / "tools/inspect_lha_archive.py"
BIND = ROOT / "tools/bind_plan_sources.py"


def make_lh0_member(name: str, payload: bytes) -> bytes:
    name_b = name.encode("latin-1")
    header_size = 22 + len(name_b)
    header = bytearray(header_size + 2)
    header[0] = header_size
    header[1] = 0
    header[2:7] = b"-lh0-"
    struct.pack_into("<I", header, 7, len(payload))
    struct.pack_into("<I", header, 11, len(payload))
    struct.pack_into("<I", header, 15, 0)
    header[19] = 0x20
    header[20] = 0
    header[21] = len(name_b)
    header[22:22 + len(name_b)] = name_b
    header[22 + len(name_b):24 + len(name_b)] = b"\x00\x00"
    return bytes(header) + payload


def run(script: Path, *args: str, expect: int = 0) -> str:
    proc = subprocess.run(
        [sys.executable, str(script), *args], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if proc.returncode != expect:
        print(proc.stdout, end="")
        raise SystemExit(
            f"M4.2 FAIL: {script.name} returned {proc.returncode}, expected {expect}"
        )
    return proc.stdout


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"M4.2 FAIL: {label} missing {needle!r}")


def main() -> int:
    required = [INSPECT, BIND, ROOT / "docs/M4_2_ARCHIVE_INSPECTION.md"]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        raise SystemExit("M4.2 FAIL: missing files: " + ", ".join(missing))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        archive = tmp / "sample.lha"
        archive.write_bytes(
            make_lh0_member("C/sample", b"hello") +
            make_lh0_member("Libs/sample.library", b"library") +
            b"\x00"
        )
        inventory = tmp / "inventory.state"
        out = run(INSPECT, "--archive", str(archive), "--inventory", str(inventory))
        require(out, "inspected 2 LhA members", "inspection")
        inv = inventory.read_text(encoding="utf-8")
        require(inv, "member.1=C/sample|-lh0-|5|5", "inventory member 1")
        require(inv, "member.2=Libs/sample.library|-lh0-|7|7", "inventory member 2")
        require(inv, "extract_ready=no", "inventory safety state")

        plan = tmp / "plan.state"
        plan.write_text(
            "format=1\n"
            "package=sample\nversion=1\nartifact=util/misc/sample.lha\n"
            + "sha256=" + "a" * 64 + "\n"
            "action_count=3\n"
            "action.1=mkdir|SYS:Tools/Sample\n"
            "action.2=copy|C/sample|C:sample\n"
            "action.3=copy|Libs/sample.library|LIBS:sample.library\n"
            "status=planned\ninstall_ready=no\n",
            encoding="utf-8",
        )
        bound = tmp / "bound.state"
        out = run(BIND, "--plan", str(plan), "--inventory", str(inventory),
                  "--output", str(bound))
        require(out, "bound 2 copy sources", "binding")
        body = bound.read_text(encoding="utf-8")
        require(body, "status=sources-validated", "bound state")
        require(body, "extract_ready=no", "bound extraction gate")
        require(body, "install_ready=no", "bound install gate")

        # Missing source must fail and preserve an existing complete output.
        original = body
        bad_plan = tmp / "bad-plan.state"
        bad_plan.write_text(plan.read_text(encoding="utf-8").replace(
            "Libs/sample.library", "Libs/missing.library"), encoding="utf-8")
        out = run(BIND, "--plan", str(bad_plan), "--inventory", str(inventory),
                  "--output", str(bound), expect=1)
        require(out, "copy source missing from archive", "missing source rejection")
        if bound.read_text(encoding="utf-8") != original:
            raise SystemExit("M4.2 FAIL: failed binding replaced valid bound state")

        # Archive traversal must be rejected during inspection.
        evil = tmp / "evil.lha"
        evil.write_bytes(make_lh0_member("../evil", b"x") + b"\x00")
        out = run(INSPECT, "--archive", str(evil), "--inventory", str(tmp / "evil.inv"), expect=1)
        require(out, "unsafe archive member path", "archive traversal rejection")

        # Unsupported header levels fail closed.
        unsupported = bytearray(make_lh0_member("C/test", b"x") + b"\x00")
        unsupported[20] = 1
        bad_archive = tmp / "level1.lha"
        bad_archive.write_bytes(bytes(unsupported))
        out = run(INSPECT, "--archive", str(bad_archive),
                  "--inventory", str(tmp / "level1.inv"), expect=1)
        require(out, "unsupported LhA header level", "unsupported level rejection")

    print("M4.2 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
