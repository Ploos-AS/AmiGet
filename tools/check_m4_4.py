#!/usr/bin/env python3
"""AmiGet M4.4 host-side qualification gate."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/plan_install_transaction.py"
DOC = ROOT / "docs/M4_4_TRANSACTION_DRY_RUN.md"


def run(*args: str, expect: int = 0) -> str:
    proc = subprocess.run(
        [sys.executable, str(TOOL), *args], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if proc.returncode != expect:
        print(proc.stdout, end="")
        raise SystemExit(f"M4.4 FAIL: planner returned {proc.returncode}, expected {expect}")
    return proc.stdout


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"M4.4 FAIL: {label} missing {needle!r}")


def write_plan(path: Path, duplicate: bool = False) -> None:
    second_dest = "C:sample" if duplicate else "LIBS:sample.library"
    path.write_text(
        "format=1\n"
        "package=sample\n"
        "version=1\n"
        "artifact=util/misc/sample.lha\n"
        + "sha256=" + "a" * 64 + "\n"
        "action_count=3\n"
        "action.1=mkdir|SYS:Tools/Sample\n"
        "action.2=copy|C/sample|C:sample\n"
        f"action.3=copy|Libs/sample.library|{second_dest}\n"
        "status=planned\n"
        "install_ready=no\n",
        encoding="utf-8",
    )


def write_state(path: Path, staging: Path) -> None:
    path.write_text(
        "format=1\n"
        "archive=/tmp/sample.lha\n"
        f"staging={staging}\n"
        "member_count=2\n"
        "member.1=C/sample|-lh0-|5\n"
        "member.2=Libs/sample.library|-lh0-|7\n"
        "status=extracted-staging\n"
        "extract_ready=yes\n"
        "install_ready=no\n",
        encoding="utf-8",
    )


def main() -> int:
    for path in (TOOL, DOC):
        if not path.is_file():
            raise SystemExit(f"M4.4 FAIL: missing {path.relative_to(ROOT)}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        staging = tmp / "stage"
        (staging / "C").mkdir(parents=True)
        (staging / "Libs").mkdir(parents=True)
        (staging / "C/sample").write_bytes(b"hello")
        (staging / "Libs/sample.library").write_bytes(b"library")
        plan = tmp / "plan.state"
        state = tmp / "extract.state"
        output = tmp / "transaction.state"
        write_plan(plan)
        write_state(state, staging)

        out = run("--plan", str(plan), "--extract-state", str(state),
                  "--staging", str(staging), "--output", str(output))
        require(out, "planned 3 actions", "success output")
        body = output.read_text(encoding="utf-8")
        require(body, "action.1=mkdir|SYS:Tools/Sample", "mkdir action")
        require(body, "action.2=copy|C/sample|C:sample|5", "copy action 1")
        require(body, "action.3=copy|Libs/sample.library|LIBS:sample.library|7", "copy action 2")
        require(body, "copy_bytes=12", "copy byte accounting")
        require(body, "transaction_ready=yes", "transaction gate")
        require(body, "install_ready=no", "install safety gate")

        missing = tmp / "missing"
        missing.mkdir()
        (missing / "C").mkdir()
        (missing / "C/sample").write_bytes(b"hello")
        missing_state = tmp / "missing.state"
        write_state(missing_state, missing)
        out = run("--plan", str(plan), "--extract-state", str(missing_state),
                  "--staging", str(missing), "--output", str(tmp / "missing.out"), expect=1)
        require(out, "staged copy source missing", "missing staged source refusal")

        dup_plan = tmp / "duplicate.plan"
        write_plan(dup_plan, duplicate=True)
        out = run("--plan", str(dup_plan), "--extract-state", str(state),
                  "--staging", str(staging), "--output", str(tmp / "duplicate.out"), expect=1)
        require(out, "duplicate copy destination", "duplicate destination refusal")

        bad_plan = tmp / "bad.plan"
        bad_plan.write_text(plan.read_text(encoding="utf-8").replace(
            "SYS:Tools/Sample", "SYS:Tools/../Danger"), encoding="utf-8")
        out = run("--plan", str(bad_plan), "--extract-state", str(state),
                  "--staging", str(staging), "--output", str(tmp / "bad.out"), expect=1)
        require(out, "unsafe Amiga destination", "destination traversal refusal")

        wrong_state = tmp / "wrong.state"
        write_state(wrong_state, tmp / "other-stage")
        out = run("--plan", str(plan), "--extract-state", str(wrong_state),
                  "--staging", str(staging), "--output", str(tmp / "wrong.out"), expect=1)
        require(out, "does not match staging path", "state/staging mismatch refusal")

    print("M4.4 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
