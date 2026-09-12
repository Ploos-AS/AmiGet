#!/usr/bin/env python3
"""Promote a verified AmiGet staging manifest to ready-for-plan state.

M3.4 is a policy/state gate only. It does not unpack or install artifacts.
The verified M3.2 manifest remains immutable input; promotion writes a separate
state file atomically after re-validating required fields and SHA-256 shape.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import tempfile

REQUIRED = {
    "format", "artifact", "staged_file", "size_bytes", "sha256",
    "status", "install_ready",
}


def load_manifest(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as fp:
        for raw in fp:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(f"malformed manifest line: {line}")
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key or not value:
                raise ValueError("empty manifest key/value")
            if key in fields:
                raise ValueError(f"duplicate manifest field: {key}")
            fields[key] = value

    missing = sorted(REQUIRED - fields.keys())
    if missing:
        raise ValueError("missing manifest fields: " + ", ".join(missing))
    return fields


def validate_manifest(fields: dict[str, str]) -> None:
    if fields["format"] != "1":
        raise ValueError("unsupported manifest format")
    if fields["status"] != "verified":
        raise ValueError("manifest status must be verified")
    if fields["install_ready"] != "no":
        raise ValueError("verified manifest must have install_ready=no")
    if not fields["size_bytes"].isdigit() or int(fields["size_bytes"]) <= 0:
        raise ValueError("invalid staged artifact size")
    digest = fields["sha256"].lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("invalid SHA-256 in verified manifest")
    staged = Path(fields["staged_file"])
    if not staged.is_file():
        raise ValueError(f"staged artifact not found: {staged}")
    if staged.stat().st_size != int(fields["size_bytes"]):
        raise ValueError("staged artifact size changed since verification")


def write_state_atomic(path: Path, fields: dict[str, str], source_manifest: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        "format=1\n"
        f"artifact={fields['artifact']}\n"
        f"staged_file={fields['staged_file']}\n"
        f"size_bytes={fields['size_bytes']}\n"
        f"sha256={fields['sha256'].lower()}\n"
        f"verified_manifest={source_manifest}\n"
        "status=ready-for-plan\n"
        "install_ready=no\n"
    )
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


def promote(manifest: Path, state: Path) -> int:
    fields = load_manifest(manifest)
    validate_manifest(fields)
    write_state_atomic(state, fields, manifest)
    print(f"AmiGet: promoted verified artifact: {fields['artifact']}")
    print("AmiGet: status=ready-for-plan")
    print("AmiGet: install_ready=no")
    print(f"AmiGet: state {state}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, help="verified M3.2 manifest")
    parser.add_argument("--state", required=True, help="ready-for-plan state output")
    args = parser.parse_args()
    try:
        return promote(Path(args.manifest), Path(args.state))
    except (OSError, ValueError) as exc:
        print(f"AmiGet: promotion refused: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
