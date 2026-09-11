#!/usr/bin/env python3
"""Fetch Aminet INDEX atomically for M2 development/qualification.

This is a host-side transport helper. It is intentionally separate from the
classic Amiga client so the INDEX parser/cache format is not tied to one TLS or
TCP/IP stack.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import tempfile
import urllib.error
import urllib.request

MIRRORS = (
    "https://de.aminet.net/aminet/INDEX",
    "https://ftp.fau.de/aminet/INDEX",
    "https://ftp.uni-erlangen.de/aminet/INDEX",
)
MAX_BYTES = 16 * 1024 * 1024
USER_AGENT = "Ploos-AS-AmiGet/0.2-m2"


def validate(data: bytes) -> None:
    if not data:
        raise ValueError("empty INDEX")
    if len(data) > MAX_BYTES:
        raise ValueError("INDEX exceeds safety limit")
    text = data[:65536].decode("latin-1", errors="replace")
    candidates = [line for line in text.splitlines() if line and not line.startswith("#")]
    if not any("/" in line and "." in line for line in candidates):
        raise ValueError("content does not look like an Aminet INDEX")


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        length = response.headers.get("Content-Length")
        if length is not None and int(length) > MAX_BYTES:
            raise ValueError("remote INDEX exceeds safety limit")
        data = response.read(MAX_BYTES + 1)
    validate(data)
    return data


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        temp_path = Path(tmp.name)
    temp_path.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="build/aminet/INDEX")
    parser.add_argument("--url", help="override mirror URL")
    args = parser.parse_args()

    urls = (args.url,) if args.url else MIRRORS
    errors: list[str] = []
    for url in urls:
        try:
            data = fetch(url)
            write_atomic(Path(args.output), data)
            print(f"Aminet INDEX: {len(data)} bytes from {url}")
            return 0
        except (OSError, ValueError, urllib.error.URLError) as exc:
            errors.append(f"{url}: {exc}")

    for error in errors:
        print(error)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
