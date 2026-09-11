#!/usr/bin/env python3
"""Verify one staged AmiGet artifact and write a manifest atomically.

M3.2 is deliberately fail-closed: a manifest with status=verified is only
written after the complete staged artifact matches the expected SHA-256.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import tempfile

CHUNK = 64 * 1024


def validate_artifact_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or value.startswith("/") or "\\" in value:
        raise ValueError("artifact path must be relative")
    if any(part in ("", ".", "..") for part in path.parts):
        raise ValueError("unsafe artifact path")
    if len(path.parts) < 2:
        raise ValueError("artifact path must include directory and filename")
    return path.as_posix()


def validate_sha256(value: str) -> str:
    text = value.strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError("expected SHA-256 must be exactly 64 hexadecimal characters")
    return text


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as fp:
        while True:
            block = fp.read(CHUNK)
            if not block:
                break
            digest.update(block)
            total += len(block)
    return digest.hexdigest(), total


def write_manifest_atomic(path: Path, *, artifact: str, staged_file: Path,
                          size: int, sha256: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        "format=1\n"
        f"artifact={artifact}\n"
        f"staged_file={staged_file}\n"
        f"size_bytes={size}\n"
        f"sha256={sha256}\n"
        "status=verified\n"
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


def verify(staged_file: Path, artifact: str, expected_sha256: str,
           manifest: Path) -> int:
    artifact = validate_artifact_path(artifact)
    expected = validate_sha256(expected_sha256)
    if not staged_file.is_file():
        print(f"AmiGet: staged artifact not found: {staged_file}")
        return 1

    actual, size = sha256_file(staged_file)
    if actual != expected:
        print("AmiGet: SHA-256 mismatch")
        print(f"AmiGet: expected {expected}")
        print(f"AmiGet: actual   {actual}")
        return 1

    write_manifest_atomic(
        manifest,
        artifact=artifact,
        staged_file=staged_file,
        size=size,
        sha256=actual,
    )
    print(f"AmiGet: verified {artifact}")
    print(f"AmiGet: sha256 {actual}")
    print(f"AmiGet: manifest {manifest}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", help="canonical Aminet artifact path")
    parser.add_argument("--file", required=True, help="staged artifact file")
    parser.add_argument("--sha256", required=True, help="expected SHA-256")
    parser.add_argument("--manifest", required=True, help="manifest output path")
    args = parser.parse_args()

    try:
        return verify(
            Path(args.file), args.artifact, args.sha256, Path(args.manifest)
        )
    except (OSError, ValueError) as exc:
        print(f"AmiGet: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
