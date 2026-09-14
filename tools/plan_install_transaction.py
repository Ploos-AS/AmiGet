#!/usr/bin/env python3
"""Build an AmiGet M4.4 install transaction dry-run.

The planner combines an M4 install plan with an M4.3 staging tree and emits a
fully resolved transaction description. It never writes to Amiga destinations.
"""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import tempfile

MAX_ACTIONS = 4096


def load_kv(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as fp:
        for raw in fp:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(f"malformed key/value line in {path}: {line}")
            key, value = line.split("=", 1)
            if key in fields:
                raise ValueError(f"duplicate field in {path}: {key}")
            fields[key] = value
    return fields


def safe_source(value: str) -> str:
    value = value.replace("\\", "/")
    path = PurePosixPath(value)
    if not value or value.startswith("/") or ":" in value:
        raise ValueError("unsafe copy source")
    if any(part in ("", ".", "..") for part in path.parts):
        raise ValueError("unsafe copy source")
    return path.as_posix()


def safe_amiga_destination(value: str) -> str:
    if not value or "|" in value or "\n" in value or "\r" in value:
        raise ValueError("unsafe Amiga destination")
    if value.startswith("/") or value.startswith("\\"):
        raise ValueError("unsafe Amiga destination")
    if value.count(":") > 1:
        raise ValueError("unsafe Amiga destination")
    if ":" in value:
        assign, rest = value.split(":", 1)
        if not assign or "/" in assign or "\\" in assign:
            raise ValueError("unsafe Amiga destination")
        path_text = rest.replace("\\", "/")
    else:
        path_text = value.replace("\\", "/")
    if any(part in (".", "..") for part in PurePosixPath(path_text).parts):
        raise ValueError("unsafe Amiga destination")
    return value


def parse_actions(plan: dict[str, str], staging: Path) -> list[tuple[str, ...]]:
    if plan.get("format") != "1" or plan.get("status") != "planned":
        raise ValueError("install plan is not planned")
    if plan.get("install_ready") != "no":
        raise ValueError("unexpected install_ready state")
    count_text = plan.get("action_count", "")
    if not count_text.isdigit():
        raise ValueError("invalid install plan action count")
    count = int(count_text)
    if count <= 0 or count > MAX_ACTIONS:
        raise ValueError("invalid install plan action count")

    actions: list[tuple[str, ...]] = []
    destinations: set[str] = set()
    for index in range(1, count + 1):
        raw = plan.get(f"action.{index}")
        if raw is None:
            raise ValueError("install plan action sequence is incomplete")
        parts = raw.split("|")
        if parts[0] == "mkdir":
            if len(parts) != 2:
                raise ValueError("malformed mkdir action")
            destination = safe_amiga_destination(parts[1])
            actions.append(("mkdir", destination))
            continue
        if parts[0] == "copy":
            if len(parts) != 3:
                raise ValueError("malformed copy action")
            source = safe_source(parts[1])
            destination = safe_amiga_destination(parts[2])
            if destination.casefold() in destinations:
                raise ValueError(f"duplicate copy destination: {destination}")
            destinations.add(destination.casefold())
            host_source = staging.joinpath(*PurePosixPath(source).parts)
            if not host_source.is_file():
                raise ValueError(f"staged copy source missing: {source}")
            actions.append(("copy", source, destination, str(host_source.stat().st_size)))
            continue
        raise ValueError(f"unsupported install action: {parts[0]}")
    return actions


def validate_extract_state(state: dict[str, str], staging: Path) -> None:
    if state.get("format") != "1" or state.get("status") != "extracted-staging":
        raise ValueError("extraction state is not qualified staging")
    if state.get("extract_ready") != "yes" or state.get("install_ready") != "no":
        raise ValueError("unexpected extraction readiness state")
    recorded = state.get("staging")
    if recorded is None or Path(recorded).resolve() != staging.resolve():
        raise ValueError("extraction state does not match staging path")
    if not staging.is_dir():
        raise ValueError("staging directory not found")


def write_transaction(path: Path, plan_path: Path, state_path: Path,
                      staging: Path, plan: dict[str, str],
                      actions: list[tuple[str, ...]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    copy_bytes = sum(int(a[3]) for a in actions if a[0] == "copy")
    lines = [
        "format=1",
        f"package={plan.get('package', '')}",
        f"version={plan.get('version', '')}",
        f"source_plan={plan_path}",
        f"source_extract_state={state_path}",
        f"staging={staging}",
        f"action_count={len(actions)}",
        f"copy_bytes={copy_bytes}",
    ]
    for index, action in enumerate(actions, start=1):
        lines.append(f"action.{index}=" + "|".join(action))
    lines.extend([
        "status=transaction-dry-run",
        "transaction_ready=yes",
        "install_ready=no",
        "",
    ])
    temp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=path.parent, delete=False) as fp:
            temp = Path(fp.name)
            fp.write("\n".join(lines))
            fp.flush()
        temp.replace(path)
    except Exception:
        if temp is not None:
            temp.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--extract-state", required=True)
    parser.add_argument("--staging", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        plan_path = Path(args.plan)
        state_path = Path(args.extract_state)
        staging = Path(args.staging)
        plan = load_kv(plan_path)
        state = load_kv(state_path)
        validate_extract_state(state, staging)
        actions = parse_actions(plan, staging)
        write_transaction(Path(args.output), plan_path, state_path, staging, plan, actions)
        print(f"AmiGet: transaction dry-run planned {len(actions)} actions")
        print("AmiGet: status=transaction-dry-run")
        print("AmiGet: transaction_ready=yes")
        print("AmiGet: install_ready=no")
        return 0
    except (OSError, ValueError) as exc:
        print(f"AmiGet: transaction dry-run refused: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
