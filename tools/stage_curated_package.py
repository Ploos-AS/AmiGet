#!/usr/bin/env python3
"""Stage and verify one curated AmiGet package.

M3.3 binds trusted curated package metadata to the M3.1 downloader and M3.2
SHA-256 verifier. It does not install or unpack the artifact.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from fetch_aminet_artifact import fetch_artifact, validate_artifact_path  # noqa: E402
from verify_staged_artifact import validate_sha256, verify  # noqa: E402

REQUIRED_FIELDS = {
    "format", "name", "version", "summary", "source", "aminet_path",
    "os_min", "cpu_min", "archive", "sha256", "install_recipe",
}


def load_recipe(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as fp:
        for raw in fp:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(f"malformed package recipe line: {line}")
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key or not value:
                raise ValueError("empty package recipe key/value")
            fields[key] = value

    missing = sorted(REQUIRED_FIELDS - fields.keys())
    if missing:
        raise ValueError("missing package fields: " + ", ".join(missing))
    if fields["source"].lower() != "aminet":
        raise ValueError("M3.3 only supports source=aminet")
    validate_artifact_path(fields["aminet_path"])
    validate_sha256(fields["sha256"])
    return fields


def safe_leaf(value: str) -> str:
    if not value or value in {".", ".."} or "/" in value or "\\" in value or ":" in value:
        raise ValueError("unsafe package name")
    return value


def stage_package(recipe_path: Path, staging_dir: Path, mirror_config: Path,
                  explicit_url: str | None = None, size_hint: str | None = None) -> int:
    fields = load_recipe(recipe_path)
    name = safe_leaf(fields["name"])
    artifact = fields["aminet_path"]
    filename = Path(artifact).name

    staging_dir.mkdir(parents=True, exist_ok=True)
    staged_file = staging_dir / filename
    manifest = staging_dir / f"{name}.manifest"

    rc = fetch_artifact(
        artifact,
        staged_file,
        size_hint,
        mirror_config,
        explicit_url,
    )
    if rc != 0:
        print(f"AmiGet: package staging failed before verification: {name}")
        return rc

    rc = verify(staged_file, artifact, fields["sha256"], manifest)
    if rc != 0:
        print(f"AmiGet: package verification failed: {name}")
        return rc

    print(f"AmiGet: curated package staged and verified: {name} {fields['version']}")
    print(f"AmiGet: install recipe reserved: {fields['install_recipe']}")
    print("AmiGet: install_ready=no")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", help="curated .pkg recipe")
    parser.add_argument("--staging-dir", required=True)
    parser.add_argument("--mirrors", default="config/mirrors.conf")
    parser.add_argument("--url", help="explicit artifact URL for qualification/testing")
    parser.add_argument("--size", help="optional coarse INDEX size sanity hint")
    args = parser.parse_args()

    try:
        return stage_package(
            Path(args.package),
            Path(args.staging_dir),
            Path(args.mirrors),
            args.url,
            args.size,
        )
    except (OSError, ValueError) as exc:
        print(f"AmiGet: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
