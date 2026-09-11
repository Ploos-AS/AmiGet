#!/usr/bin/env python3
"""AmiGet M3.2 host-side qualification gate."""

from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "tools/verify_staged_artifact.py"


def run(*args: str, expect: int = 0) -> str:
    proc = subprocess.run(
        [sys.executable, str(VERIFY), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != expect:
        print(proc.stdout, end="")
        raise SystemExit(
            f"M3.2 FAIL: {' '.join(args)} returned {proc.returncode}, expected {expect}"
        )
    return proc.stdout


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"M3.2 FAIL: {label} missing {needle!r}")


def main() -> int:
    required = [VERIFY, ROOT / "docs/M3_2_VERIFICATION.md"]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        raise SystemExit("M3.2 FAIL: missing files: " + ", ".join(missing))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        staged = tmp / "staging" / "sample.lha"
        staged.parent.mkdir(parents=True)
        staged.write_bytes((b"AmiGet-M3.2\n" * 257) + b"end")
        good = hashlib.sha256(staged.read_bytes()).hexdigest()
        bad = "0" * 64
        manifest = tmp / "state" / "sample.manifest"

        out = run(
            "util/cli/sample.lha",
            "--file", str(staged),
            "--sha256", good,
            "--manifest", str(manifest),
        )
        require(out, "verified util/cli/sample.lha", "successful verification")
        require(out, good, "successful verification digest")
        text = manifest.read_text(encoding="utf-8")
        for needle in (
            "format=1",
            "artifact=util/cli/sample.lha",
            f"size_bytes={staged.stat().st_size}",
            f"sha256={good}",
            "status=verified",
            "install_ready=no",
        ):
            require(text, needle, "manifest")

        original_manifest = text
        out = run(
            "util/cli/sample.lha",
            "--file", str(staged),
            "--sha256", bad,
            "--manifest", str(manifest),
            expect=1,
        )
        require(out, "SHA-256 mismatch", "mismatch rejection")
        if manifest.read_text(encoding="utf-8") != original_manifest:
            raise SystemExit("M3.2 FAIL: failed verification changed trusted manifest")

        fresh_manifest = tmp / "state" / "fresh.manifest"
        out = run(
            "util/cli/sample.lha",
            "--file", str(staged),
            "--sha256", bad,
            "--manifest", str(fresh_manifest),
            expect=1,
        )
        if fresh_manifest.exists():
            raise SystemExit("M3.2 FAIL: mismatch created a verification manifest")

        out = run(
            "../sample.lha",
            "--file", str(staged),
            "--sha256", good,
            "--manifest", str(fresh_manifest),
            expect=1,
        )
        require(out, "unsafe artifact path", "path traversal rejection")

        out = run(
            "util/cli/sample.lha",
            "--file", str(staged),
            "--sha256", "not-a-digest",
            "--manifest", str(fresh_manifest),
            expect=1,
        )
        require(out, "64 hexadecimal", "digest validation")

    print("M3.2 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
