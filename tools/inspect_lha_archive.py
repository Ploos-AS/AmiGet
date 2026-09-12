#!/usr/bin/env python3
"""Inspect classic LhA archives without extracting them.

M4.2 deliberately supports only level-0 LhA headers. Unsupported header levels
fail closed. The output inventory is suitable for binding install-plan copy
sources before any extraction or installation is attempted.
"""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import struct
import tempfile

MAX_ENTRIES = 4096
MAX_NAME = 255
MAX_PACKED = 512 * 1024 * 1024


def validate_member_name(value: str) -> str:
    value = value.replace("\\", "/")
    path = PurePosixPath(value)
    if not value or value.startswith("/") or ":" in value:
        raise ValueError("unsafe archive member path")
    if any(part in ("", ".", "..") for part in path.parts):
        raise ValueError("unsafe archive member path")
    return path.as_posix()


def inspect_level0(path: Path) -> list[tuple[str, str, int, int]]:
    entries: list[tuple[str, str, int, int]] = []
    data = path.read_bytes()
    offset = 0
    while offset < len(data):
        header_size = data[offset]
        if header_size == 0:
            break
        total_header = header_size + 2
        if total_header < 24 or offset + total_header > len(data):
            raise ValueError("truncated or invalid LhA header")
        h = data[offset : offset + total_header]
        if len(h) < 24:
            raise ValueError("truncated LhA header")
        method = h[2:7].decode("ascii", errors="strict")
        if not (method.startswith("-lh") or method == "-lzs-"):
            raise ValueError("unsupported LhA compression method marker")
        packed_size = struct.unpack_from("<I", h, 7)[0]
        original_size = struct.unpack_from("<I", h, 11)[0]
        level = h[20]
        if level != 0:
            raise ValueError(f"unsupported LhA header level: {level}")
        name_len = h[21]
        if name_len == 0 or name_len > MAX_NAME:
            raise ValueError("invalid LhA member name length")
        name_end = 22 + name_len
        if name_end + 2 > len(h):
            raise ValueError("truncated LhA member name")
        try:
            name = h[22:name_end].decode("latin-1")
        except UnicodeDecodeError as exc:
            raise ValueError("invalid LhA member name") from exc
        name = validate_member_name(name)
        if packed_size > MAX_PACKED:
            raise ValueError("LhA member exceeds safety limit")
        data_start = offset + total_header
        data_end = data_start + packed_size
        if data_end > len(data):
            raise ValueError("truncated LhA member data")
        entries.append((name, method, packed_size, original_size))
        if len(entries) > MAX_ENTRIES:
            raise ValueError("too many LhA members")
        offset = data_end
    if not entries:
        raise ValueError("LhA archive contains no inspectable members")
    return entries


def write_inventory_atomic(path: Path, archive: Path,
                           entries: list[tuple[str, str, int, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["format=1", f"archive={archive}", f"member_count={len(entries)}"]
    for index, (name, method, packed, original) in enumerate(entries, start=1):
        lines.append(f"member.{index}={name}|{method}|{packed}|{original}")
    lines.extend(["status=inspected", "extract_ready=no", ""])
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
    parser.add_argument("--archive", required=True)
    parser.add_argument("--inventory", required=True)
    args = parser.parse_args()
    try:
        archive = Path(args.archive)
        if not archive.is_file():
            raise ValueError(f"archive not found: {archive}")
        entries = inspect_level0(archive)
        write_inventory_atomic(Path(args.inventory), archive, entries)
        print(f"AmiGet: inspected {len(entries)} LhA members")
        print("AmiGet: status=inspected")
        print("AmiGet: extract_ready=no")
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"AmiGet: archive inspection refused: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
