#!/usr/bin/env python3
"""Extract qualified level-0 LhA members into an isolated staging tree.

M4.3 is intentionally conservative. Only -lh0- members are extracted by this
host-side reference implementation. Paths are revalidated and extraction never
writes outside the requested staging directory. Installation to Amiga assigns
remains out of scope.
"""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import shutil
import struct
import tempfile

MAX_ENTRIES = 4096
MAX_NAME = 255
MAX_MEMBER_SIZE = 512 * 1024 * 1024
MAX_TOTAL_SIZE = 1024 * 1024 * 1024


def validate_member_name(value: str) -> str:
    value = value.replace("\\", "/")
    path = PurePosixPath(value)
    if not value or value.startswith("/") or ":" in value:
        raise ValueError("unsafe archive member path")
    if any(part in ("", ".", "..") for part in path.parts):
        raise ValueError("unsafe archive member path")
    return path.as_posix()


def parse_level0(path: Path) -> list[tuple[str, str, bytes]]:
    entries: list[tuple[str, str, bytes]] = []
    data = path.read_bytes()
    offset = 0
    total_original = 0

    while offset < len(data):
        header_size = data[offset]
        if header_size == 0:
            break
        total_header = header_size + 2
        if total_header < 24 or offset + total_header > len(data):
            raise ValueError("truncated or invalid LhA header")
        h = data[offset:offset + total_header]
        method = h[2:7].decode("ascii", errors="strict")
        packed_size = struct.unpack_from("<I", h, 7)[0]
        original_size = struct.unpack_from("<I", h, 11)[0]
        level = h[20]
        if level != 0:
            raise ValueError(f"unsupported LhA header level: {level}")
        if method != "-lh0-":
            raise ValueError(f"staging extraction does not support method: {method}")
        if packed_size != original_size:
            raise ValueError("invalid -lh0- size fields")
        if original_size > MAX_MEMBER_SIZE:
            raise ValueError("LhA member exceeds safety limit")

        name_len = h[21]
        if name_len == 0 or name_len > MAX_NAME:
            raise ValueError("invalid LhA member name length")
        name_end = 22 + name_len
        if name_end + 2 > len(h):
            raise ValueError("truncated LhA member name")
        name = validate_member_name(h[22:name_end].decode("latin-1"))

        data_start = offset + total_header
        data_end = data_start + packed_size
        if data_end > len(data):
            raise ValueError("truncated LhA member data")

        total_original += original_size
        if total_original > MAX_TOTAL_SIZE:
            raise ValueError("archive exceeds total extraction safety limit")
        entries.append((name, method, data[data_start:data_end]))
        if len(entries) > MAX_ENTRIES:
            raise ValueError("too many LhA members")
        offset = data_end

    if not entries:
        raise ValueError("LhA archive contains no extractable members")
    return entries


def safe_destination(root: Path, member: str) -> Path:
    destination = root.joinpath(*PurePosixPath(member).parts)
    root_resolved = root.resolve()
    parent_resolved = destination.parent.resolve()
    if parent_resolved != root_resolved and root_resolved not in parent_resolved.parents:
        raise ValueError("staging destination escapes root")
    return destination


def write_state(path: Path, archive: Path, staging: Path,
                entries: list[tuple[str, str, bytes]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "format=1",
        f"archive={archive}",
        f"staging={staging}",
        f"member_count={len(entries)}",
    ]
    for index, (name, method, payload) in enumerate(entries, start=1):
        lines.append(f"member.{index}={name}|{method}|{len(payload)}")
    lines.extend([
        "status=extracted-staging",
        "extract_ready=yes",
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


def extract_atomic(archive: Path, staging: Path, state: Path) -> int:
    entries = parse_level0(archive)
    staging_parent = staging.parent
    staging_parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix=staging.name + ".tmp-", dir=staging_parent))
    try:
        for name, _method, payload in entries:
            destination = safe_destination(temp_root, name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise ValueError(f"duplicate archive member path: {name}")
            destination.write_bytes(payload)

        if staging.exists():
            raise ValueError(f"staging destination already exists: {staging}")
        temp_root.replace(staging)
        temp_root = staging
        write_state(state, archive, staging, entries)
        return len(entries)
    except Exception:
        if temp_root.exists() and temp_root != staging:
            shutil.rmtree(temp_root, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--staging", required=True)
    parser.add_argument("--state", required=True)
    args = parser.parse_args()

    try:
        archive = Path(args.archive)
        if not archive.is_file():
            raise ValueError(f"archive not found: {archive}")
        count = extract_atomic(archive, Path(args.staging), Path(args.state))
        print(f"AmiGet: extracted {count} LhA members to staging")
        print("AmiGet: status=extracted-staging")
        print("AmiGet: extract_ready=yes")
        print("AmiGet: install_ready=no")
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"AmiGet: staging extraction refused: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
