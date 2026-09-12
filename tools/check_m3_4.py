#!/usr/bin/env python3
"""AmiGet M3.4 host-side qualification gate."""

from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROMOTE = ROOT / "tools/promote_verified_stage.py"


def run(*args: str, expect: int = 0) -> str:
    proc = subprocess.run(
        [sys.executable, str(PROMOTE), *args], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if proc.returncode != expect:
        print(proc.stdout, end="")
        raise SystemExit(
            f"M3.4 FAIL: {' '.join(args)} returned {proc.returncode}, expected {expect}"
        )
    return proc.stdout


def main() -> int:
    required = [PROMOTE, ROOT / "docs/M3_4_PROMOTION_GATE.md"]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        raise SystemExit("M3.4 FAIL: missing files: " + ", ".join(missing))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        artifact = tmp / "sample.lha"
        artifact.write_bytes(b"verified-stage" * 128)
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        manifest = tmp / "sample.manifest"
        state = tmp / "sample.ready"
        manifest.write_text(
            "format=1\n"
            "artifact=util/cli/sample.lha\n"
            f"staged_file={artifact}\n"
            f"size_bytes={artifact.stat().st_size}\n"
            f"sha256={digest}\n"
            "status=verified\n"
            "install_ready=no\n",
            encoding="utf-8",
        )

        out = run("--manifest", str(manifest), "--state", str(state))
        if "status=ready-for-plan" not in out:
            raise SystemExit("M3.4 FAIL: promotion status missing")
        body = state.read_text(encoding="utf-8")
        for needle in (
            "status=ready-for-plan",
            "install_ready=no",
            f"sha256={digest}",
            "artifact=util/cli/sample.lha",
        ):
            if needle not in body:
                raise SystemExit(f"M3.4 FAIL: state missing {needle!r}")

        original = body
        bad_manifest = tmp / "bad.manifest"
        bad_manifest.write_text(manifest.read_text(encoding="utf-8").replace(
            "status=verified", "status=downloaded"
        ), encoding="utf-8")
        out = run("--manifest", str(bad_manifest), "--state", str(state), expect=1)
        if "must be verified" not in out:
            raise SystemExit("M3.4 FAIL: unverified manifest not clearly refused")
        if state.read_text(encoding="utf-8") != original:
            raise SystemExit("M3.4 FAIL: failed promotion overwrote valid state")

        tampered = tmp / "tampered.manifest"
        tampered.write_text(manifest.read_text(encoding="utf-8").replace(
            f"size_bytes={artifact.stat().st_size}", "size_bytes=1"
        ), encoding="utf-8")
        out = run("--manifest", str(tampered), "--state", str(state), expect=1)
        if "size changed" not in out:
            raise SystemExit("M3.4 FAIL: changed staged artifact size not refused")

    print("M3.4 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
