#!/usr/bin/env python3
"""Bind an M4.1 install plan to an inspected archive inventory.

Every copy source must exist exactly in the inspected archive inventory before a
plan can advance. This tool still performs no extraction or installation.
"""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import tempfile


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


def safe_member(value: str) -> str:
    value = value.replace("\\", "/")
    p = PurePosixPath(value)
    if not value or value.startswith("/") or ":" in value:
        raise ValueError("unsafe copy source")
    if any(part in ("", ".", "..") for part in p.parts):
        raise ValueError("unsafe copy source")
    return p.as_posix()


def inventory_members(inv: dict[str, str]) -> set[str]:
    if inv.get("format") != "1" or inv.get("status") != "inspected":
        raise ValueError("inventory is not inspected")
    count_text = inv.get("member_count", "")
    if not count_text.isdigit() or int(count_text) <= 0:
        raise ValueError("invalid inventory member count")
    count = int(count_text)
    members: set[str] = set()
    for i in range(1, count + 1):
        raw = inv.get(f"member.{i}")
        if raw is None:
            raise ValueError("inventory member sequence is incomplete")
        name = raw.split("|", 1)[0]
        name = safe_member(name)
        if name in members:
            raise ValueError(f"duplicate archive member: {name}")
        members.add(name)
    return members


def plan_copy_sources(plan: dict[str, str]) -> list[str]:
    if plan.get("format") != "1" or plan.get("status") != "planned":
        raise ValueError("install plan is not planned")
    if plan.get("install_ready") != "no":
        raise ValueError("unexpected install_ready state")
    count_text = plan.get("action_count", "")
    if not count_text.isdigit() or int(count_text) <= 0:
        raise ValueError("invalid install plan action count")
    sources: list[str] = []
    for i in range(1, int(count_text) + 1):
        raw = plan.get(f"action.{i}")
        if raw is None:
            raise ValueError("install plan action sequence is incomplete")
        parts = raw.split("|")
        if parts[0] == "copy":
            if len(parts) != 3:
                raise ValueError("malformed copy action")
            sources.append(safe_member(parts[1]))
    if not sources:
        raise ValueError("install plan contains no copy actions to bind")
    return sources


def write_bound_atomic(path: Path, plan_path: Path, inventory_path: Path,
                       plan: dict[str, str], sources: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "format=1",
        f"package={plan.get('package', '')}",
        f"version={plan.get('version', '')}",
        f"artifact={plan.get('artifact', '')}",
        f"sha256={plan.get('sha256', '')}",
        f"source_plan={plan_path}",
        f"source_inventory={inventory_path}",
        f"bound_copy_count={len(sources)}",
    ]
    for i, src in enumerate(sources, start=1):
        lines.append(f"copy_source.{i}={src}")
    lines.extend(["status=sources-validated", "extract_ready=no", "install_ready=no", ""])
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


def bind(plan_path: Path, inventory_path: Path, output: Path) -> int:
    plan = load_kv(plan_path)
    inv = load_kv(inventory_path)
    members = inventory_members(inv)
    sources = plan_copy_sources(plan)
    missing = [src for src in sources if src not in members]
    if missing:
        raise ValueError("copy source missing from archive: " + ", ".join(missing))
    write_bound_atomic(output, plan_path, inventory_path, plan, sources)
    print(f"AmiGet: bound {len(sources)} copy sources to inspected archive")
    print("AmiGet: status=sources-validated")
    print("AmiGet: extract_ready=no")
    print("AmiGet: install_ready=no")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        return bind(Path(args.plan), Path(args.inventory), Path(args.output))
    except (OSError, ValueError) as exc:
        print(f"AmiGet: source binding refused: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
