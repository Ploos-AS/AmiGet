#!/usr/bin/env python3
"""AmiGet M0 repository qualification gate."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "LICENSE",
    "docs/ROADMAP.md",
    "docs/PACKAGE_FORMAT.md",
    "packages/example.pkg",
    "profiles/base.profile",
    "src/README.md",
    "include/README.md",
    "tools/check_m0.py",
]

PACKAGE_KEYS = {
    "format",
    "name",
    "version",
    "summary",
    "source",
    "aminet_path",
    "os_min",
    "cpu_min",
    "archive",
    "sha256",
    "install_recipe",
}


def parse_kv(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}: invalid line: {raw!r}")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            raise ValueError(f"{path}: empty key/value: {raw!r}")
        if key in result:
            raise ValueError(f"{path}: duplicate key: {key}")
        result[key] = value
    return result


def fail(message: str) -> None:
    print(f"M0 FAIL: {message}")
    raise SystemExit(1)


def main() -> int:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for marker in ("AmigaOS 2.04+", "68000", "Aminet", "M0"):
        if marker not in readme:
            fail(f"README missing marker: {marker}")

    package = parse_kv(ROOT / "packages/example.pkg")
    absent = sorted(PACKAGE_KEYS - package.keys())
    if absent:
        fail("example package missing keys: " + ", ".join(absent))
    if package["format"] != "0":
        fail("example package format must be 0")
    if package["source"] != "aminet":
        fail("M0 example source must be aminet")
    if package["aminet_path"].startswith(("http://", "https://", "/")):
        fail("aminet_path must be a relative upstream path")

    profile = parse_kv(ROOT / "profiles/base.profile")
    if profile.get("name") != "base" or "description" not in profile:
        fail("base profile metadata is invalid")

    print("M0 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
