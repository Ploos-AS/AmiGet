#!/usr/bin/env python3
"""AmiGet M3.3 host-side qualification gate."""

from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "tools/stage_curated_package.py"


def run(*args: str, expect: int = 0) -> str:
    proc = subprocess.run(
        [sys.executable, str(PIPELINE), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != expect:
        print(proc.stdout, end="")
        raise SystemExit(
            f"M3.3 FAIL: {' '.join(args)} returned {proc.returncode}, expected {expect}"
        )
    return proc.stdout


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"M3.3 FAIL: {label} missing {needle!r}")


def recipe_text(sha256: str) -> str:
    return (
        "format=0\n"
        "name=testpkg\n"
        "version=1.2.3\n"
        "summary=M3.3 qualification package\n"
        "source=aminet\n"
        "aminet_path=util/cli/testpkg.lha\n"
        "os_min=2.04\n"
        "cpu_min=68000\n"
        "archive=lha\n"
        f"sha256={sha256}\n"
        "install_recipe=manual\n"
    )


def main() -> int:
    required = [
        PIPELINE,
        ROOT / "tools/fetch_aminet_artifact.py",
        ROOT / "tools/verify_staged_artifact.py",
        ROOT / "docs/M3_3_CURATED_STAGING.md",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        raise SystemExit("M3.3 FAIL: missing files: " + ", ".join(missing))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        source = tmp / "testpkg.lha"
        source.write_bytes(b"AmiGet M3.3 qualification payload\n" * 1024)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        recipe = tmp / "testpkg.pkg"
        recipe.write_text(recipe_text(digest), encoding="utf-8")
        staging = tmp / "staging"

        out = run(
            str(recipe),
            "--staging-dir", str(staging),
            "--url", source.resolve().as_uri(),
        )
        require(out, "curated package staged and verified: testpkg 1.2.3", "pipeline")
        require(out, "install_ready=no", "pipeline")

        staged = staging / "testpkg.lha"
        manifest = staging / "testpkg.manifest"
        if staged.read_bytes() != source.read_bytes():
            raise SystemExit("M3.3 FAIL: staged bytes differ")
        body = manifest.read_text(encoding="utf-8")
        for needle in (
            "artifact=util/cli/testpkg.lha",
            f"sha256={digest}",
            "status=verified",
            "install_ready=no",
        ):
            require(body, needle, "manifest")

        # Wrong curated checksum must fail closed and must not publish a manifest.
        manifest.unlink()
        bad_recipe = tmp / "bad.pkg"
        bad_recipe.write_text(recipe_text("0" * 64), encoding="utf-8")
        out = run(
            str(bad_recipe),
            "--staging-dir", str(staging),
            "--url", source.resolve().as_uri(),
            expect=1,
        )
        require(out, "SHA-256 mismatch", "checksum mismatch")
        if manifest.exists():
            raise SystemExit("M3.3 FAIL: mismatch published verified manifest")

        # UNSET must be rejected before trust can be established.
        unset_recipe = tmp / "unset.pkg"
        unset_recipe.write_text(recipe_text("UNSET"), encoding="utf-8")
        out = run(
            str(unset_recipe),
            "--staging-dir", str(staging),
            "--url", source.resolve().as_uri(),
            expect=1,
        )
        require(out, "64 hexadecimal characters", "UNSET rejection")

    print("M3.3 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
