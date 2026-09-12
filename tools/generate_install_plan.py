#!/usr/bin/env python3
"""Generate a deterministic AmiGet install plan without changing the system.

M4.1 consumes trusted curated package metadata plus an M3.4 ready-for-plan
state. Recipes are declarative; arbitrary shell commands are not supported.
"""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import tempfile

REQUIRED_PACKAGE = {
    "format", "name", "version", "source", "aminet_path", "sha256",
    "install_recipe",
}
REQUIRED_STATE = {
    "format", "artifact", "staged_file", "size_bytes", "sha256",
    "status", "install_ready",
}
ALLOWED_ACTIONS = {"mkdir", "copy", "assign"}


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
            key = key.strip()
            value = value.strip()
            if not key or not value:
                raise ValueError(f"empty key/value in {path}")
            if key in fields:
                raise ValueError(f"duplicate field in {path}: {key}")
            fields[key] = value
    return fields


def validate_sha256(value: str) -> str:
    text = value.strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError("invalid package SHA-256")
    return text


def validate_relative_source(value: str) -> str:
    path = PurePosixPath(value)
    if not value or value.startswith("/") or "\\" in value:
        raise ValueError("copy source must be relative")
    if any(part in ("", ".", "..") for part in path.parts):
        raise ValueError("unsafe copy source")
    return path.as_posix()


def validate_amiga_path(value: str) -> str:
    if not value or ":" not in value or "\\" in value:
        raise ValueError("destination must be an AmigaOS path with an assign/device")
    if ".." in value.split("/"):
        raise ValueError("unsafe AmigaOS destination path")
    return value


def validate_assign(value: str) -> str:
    if not value or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for ch in value):
        raise ValueError("assign name must use A-Z, 0-9 or underscore")
    return value


def load_recipe(path: Path) -> tuple[str, list[str]]:
    recipe_id = ""
    actions: list[str] = []
    with path.open("r", encoding="utf-8") as fp:
        for raw in fp:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("format="):
                if line != "format=1":
                    raise ValueError("unsupported install recipe format")
                continue
            if line.startswith("recipe="):
                recipe_id = line.split("=", 1)[1].strip()
                continue
            if not line.startswith("action="):
                raise ValueError(f"unsupported recipe directive: {line}")
            spec = line.split("=", 1)[1]
            parts = spec.split("|")
            kind = parts[0]
            if kind not in ALLOWED_ACTIONS:
                raise ValueError(f"unsupported install action: {kind}")
            if kind == "mkdir":
                if len(parts) != 2:
                    raise ValueError("mkdir requires one destination")
                actions.append(f"mkdir|{validate_amiga_path(parts[1])}")
            elif kind == "copy":
                if len(parts) != 3:
                    raise ValueError("copy requires source and destination")
                src = validate_relative_source(parts[1])
                dst = validate_amiga_path(parts[2])
                actions.append(f"copy|{src}|{dst}")
            elif kind == "assign":
                if len(parts) != 3:
                    raise ValueError("assign requires name and path")
                name = validate_assign(parts[1])
                dst = validate_amiga_path(parts[2])
                actions.append(f"assign|{name}|{dst}")
    if not recipe_id:
        raise ValueError("install recipe missing recipe identifier")
    if not actions:
        raise ValueError("install recipe contains no actions")
    return recipe_id, actions


def write_plan_atomic(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as tmp:
            temp_path = Path(tmp.name)
            tmp.write(body)
            tmp.flush()
        temp_path.replace(path)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def generate(package_path: Path, state_path: Path, recipe_dir: Path, output: Path) -> int:
    package = load_kv(package_path)
    state = load_kv(state_path)
    missing_pkg = sorted(REQUIRED_PACKAGE - package.keys())
    missing_state = sorted(REQUIRED_STATE - state.keys())
    if missing_pkg:
        raise ValueError("missing package fields: " + ", ".join(missing_pkg))
    if missing_state:
        raise ValueError("missing state fields: " + ", ".join(missing_state))
    if package["source"].lower() != "aminet":
        raise ValueError("M4.1 only supports source=aminet")
    if state["status"] != "ready-for-plan" or state["install_ready"] != "no":
        raise ValueError("state is not ready-for-plan")
    if state["artifact"] != package["aminet_path"]:
        raise ValueError("package artifact does not match promoted state")
    pkg_sha = validate_sha256(package["sha256"])
    state_sha = validate_sha256(state["sha256"])
    if pkg_sha != state_sha:
        raise ValueError("package SHA-256 does not match promoted state")

    recipe_name = package["install_recipe"]
    if not recipe_name or recipe_name in {"manual", "none"}:
        raise ValueError("package has no plannable install recipe")
    if "/" in recipe_name or "\\" in recipe_name or ":" in recipe_name or recipe_name in {".", ".."}:
        raise ValueError("unsafe install recipe identifier")
    recipe_path = recipe_dir / f"{recipe_name}.recipe"
    recipe_id, actions = load_recipe(recipe_path)
    if recipe_id != recipe_name:
        raise ValueError("install recipe identifier mismatch")

    lines = [
        "format=1",
        f"package={package['name']}",
        f"version={package['version']}",
        f"artifact={package['aminet_path']}",
        f"sha256={pkg_sha}",
        f"source_state={state_path}",
        f"recipe={recipe_id}",
        f"action_count={len(actions)}",
    ]
    for index, action in enumerate(actions, start=1):
        lines.append(f"action.{index}={action}")
    lines.extend(["status=planned", "install_ready=no", ""])
    write_plan_atomic(output, "\n".join(lines))
    print(f"AmiGet: install plan generated for {package['name']} {package['version']}")
    print(f"AmiGet: actions={len(actions)}")
    print("AmiGet: status=planned")
    print("AmiGet: install_ready=no")
    print(f"AmiGet: plan {output}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--recipe-dir", default="install-recipes")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        return generate(
            Path(args.package), Path(args.state), Path(args.recipe_dir), Path(args.output)
        )
    except (OSError, ValueError) as exc:
        print(f"AmiGet: plan refused: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
