#!/usr/bin/env python3
"""AmiGet M2.3 host-side qualification gate."""

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
        [str(binary), *args], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if proc.returncode != expect:
        print(proc.stdout, end="")
        raise SystemExit(
            f"M2.3 FAIL: {binary.name} {' '.join(args)} returned "
            f"{proc.returncode}, expected {expect}"
        )
    return proc.stdout


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"M2.3 FAIL: {label} missing {needle!r}")


def main() -> int:
    for path in (AMI, IDX, FIXTURE, ROOT / "src/upstream_info.c"):
        if not path.is_file():
            raise SystemExit(f"M2.3 FAIL: missing {path.relative_to(ROOT)}")

    out = run(AMI, "version")
    require(out, "AmiGet 0.2.0-m2.3", "version")

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = Path(tmpdir) / "aminet.cache"
        run(IDX, "build", str(FIXTURE), str(cache))

        out = run(AMI, "upstream-info", "AmiSSL-5.19.lha", str(cache))
        for needle in (
            "Name:        AmiSSL-5.19.lha",
            "Source:      aminet",
            "Directory:   util/libs",
            "Artifact:    util/libs/AmiSSL-5.19.lha",
            "Size:        4M",
            "Description: SSL TLS libraries for AmigaOS",
            "Checksum:    unavailable-in-index",
            "Install:     not-planned",
        ):
            require(out, needle, "upstream info")

        # Exact lookup is case-insensitive but not substring-based.
        out = run(AMI, "upstream-info", "amissl-5.19.LHA", str(cache))
        require(out, "Artifact:    util/libs/AmiSSL-5.19.lha", "case-insensitive lookup")

        out = run(AMI, "upstream-info", "AmiSSL", str(cache), expect=2)
        require(out, "Aminet artifact not found", "non-exact lookup")

    print("M2.3 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
