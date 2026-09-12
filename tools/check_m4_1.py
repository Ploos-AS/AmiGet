#!/usr/bin/env python3
"""AmiGet M4.1 host-side qualification gate."""

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "tools/generate_install_plan.py"
PKG = ROOT / "tests/fixtures/packages/demo.pkg"
RECIPES = ROOT / "tests/fixtures/install-recipes"
SHA = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


def run(*args: str, expect: int = 0) -> str:
    proc = subprocess.run(
        [sys.executable, str(GEN), *args], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if proc.returncode != expect:
        print(proc.stdout, end="")
        raise SystemExit(
            f"M4.1 FAIL: {' '.join(args)} returned {proc.returncode}, expected {expect}"
        )
    return proc.stdout


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"M4.1 FAIL: {label} missing {needle!r}")


def main() -> int:
    required = [GEN, PKG, RECIPES / "demo.recipe", ROOT / "docs/M4_1_INSTALL_PLAN.md"]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        raise SystemExit("M4.1 FAIL: missing files: " + ", ".join(missing))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        staged = tmp / "demo.lha"
        staged.write_bytes(b"fixture")
        state = tmp / "demo.ready"
        state.write_text(
            "format=1\n"
            "artifact=util/misc/demo.lha\n"
            f"staged_file={staged}\n"
            "size_bytes=7\n"
            f"sha256={SHA}\n"
            "verified_manifest=/qualification/demo.manifest\n"
            "status=ready-for-plan\n"
            "install_ready=no\n",
            encoding="utf-8",
        )
        plan = tmp / "demo.plan"
        out = run(
            "--package", str(PKG),
            "--state", str(state),
            "--recipe-dir", str(RECIPES),
            "--output", str(plan),
        )
        require(out, "status=planned", "successful plan")
        require(out, "install_ready=no", "successful plan")
        body = plan.read_text(encoding="utf-8")
        expected = (
            "format=1\n"
            "package=demo\n"
            "version=1.0\n"
            "artifact=util/misc/demo.lha\n"
            f"sha256={SHA}\n"
            f"source_state={state}\n"
            "recipe=demo\n"
            "action_count=3\n"
            "action.1=mkdir|SYS:Demo\n"
            "action.2=copy|bin/demo|C:Demo\n"
            "action.3=assign|DEMO|SYS:Demo\n"
            "status=planned\n"
            "install_ready=no\n"
        )
        if body != expected:
            raise SystemExit("M4.1 FAIL: generated plan is not deterministic")

        original = body
        bad_state = tmp / "bad.ready"
        bad_state.write_text(state.read_text(encoding="utf-8").replace(SHA, "f" * 64), encoding="utf-8")
        out = run(
            "--package", str(PKG), "--state", str(bad_state),
            "--recipe-dir", str(RECIPES), "--output", str(plan), expect=1,
        )
        require(out, "SHA-256 does not match", "state/package binding")
        if plan.read_text(encoding="utf-8") != original:
            raise SystemExit("M4.1 FAIL: refused plan replaced existing plan")

        bad_recipe_dir = tmp / "recipes"
        bad_recipe_dir.mkdir()
        (bad_recipe_dir / "demo.recipe").write_text(
            "format=1\nrecipe=demo\naction=shell|delete SYS:#?\n", encoding="utf-8"
        )
        out = run(
            "--package", str(PKG), "--state", str(state),
            "--recipe-dir", str(bad_recipe_dir), "--output", str(plan), expect=1,
        )
        require(out, "unsupported install action", "arbitrary command rejection")
        if plan.read_text(encoding="utf-8") != original:
            raise SystemExit("M4.1 FAIL: bad recipe replaced existing plan")

    print("M4.1 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
