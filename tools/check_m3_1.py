#!/usr/bin/env python3
"""AmiGet M3.1 host-side qualification gate."""

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FETCH = ROOT / "tools/fetch_aminet_artifact.py"


def run(*args: str, expect: int = 0) -> str:
    proc = subprocess.run(
        [sys.executable, str(FETCH), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != expect:
        print(proc.stdout, end="")
        raise SystemExit(
            f"M3.1 FAIL: {' '.join(args)} returned {proc.returncode}, expected {expect}"
        )
    return proc.stdout


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"M3.1 FAIL: {label} missing {needle!r}")


def main() -> int:
    required = [
        FETCH,
        ROOT / "config/mirrors.conf",
        ROOT / "docs/M3_1_DOWNLOAD_STAGING.md",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        raise SystemExit("M3.1 FAIL: missing files: " + ", ".join(missing))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        source = tmp / "sample.lha"
        source.write_bytes(b"A" * (34 * 1024))
        output = tmp / "staging" / "sample.lha"

        out = run(
            "util/cli/sample.lha",
            "--output", str(output),
            "--size", "34K",
            "--url", source.resolve().as_uri(),
        )
        require(out, "staged util/cli/sample.lha", "successful stage")
        require(out, "staging file:", "successful stage")
        if output.read_bytes() != source.read_bytes():
            raise SystemExit("M3.1 FAIL: staged bytes differ from source")

        # A failed replacement must preserve the previous complete staging file.
        original = output.read_bytes()
        bad = tmp / "tiny.lha"
        bad.write_bytes(b"bad")
        out = run(
            "util/cli/sample.lha",
            "--output", str(output),
            "--size", "34K",
            "--url", bad.resolve().as_uri(),
            expect=1,
        )
        require(out, "implausible", "coarse size rejection")
        if output.read_bytes() != original:
            raise SystemExit("M3.1 FAIL: failed download replaced complete staging file")

        # Path traversal must be rejected before transport.
        out = run(
            "../sample.lha",
            "--output", str(output),
            "--url", source.resolve().as_uri(),
            expect=1,
        )
        require(out, "unsafe artifact path", "path traversal rejection")

        leftovers = list(output.parent.glob("tmp*"))
        if leftovers:
            raise SystemExit("M3.1 FAIL: temporary staging files were left behind")

    mirrors = (ROOT / "config/mirrors.conf").read_text(encoding="utf-8")
    if mirrors.count("https://") < 2:
        raise SystemExit("M3.1 FAIL: mirror fallback configuration missing")

    print("M3.1 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
