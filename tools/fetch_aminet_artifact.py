#!/usr/bin/env python3
"""Fetch one Aminet artifact into a staging area atomically.

M3.1 intentionally treats the INDEX size field as a coarse sanity check only.
Cryptographic verification belongs to the next verification milestone.
"""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import tempfile
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_MIRRORS = Path("config/mirrors.conf")
USER_AGENT = "Ploos-AS-AmiGet/0.3-m3.1"
MAX_BYTES = 512 * 1024 * 1024
CHUNK = 64 * 1024


def validate_artifact_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or value.startswith("/") or "\\" in value:
        raise ValueError("artifact path must be relative")
    if any(part in ("", ".", "..") for part in path.parts):
        raise ValueError("unsafe artifact path")
    if len(path.parts) < 2:
        raise ValueError("artifact path must include Aminet directory and filename")
    return path.as_posix()


def parse_size_hint(value: str | None) -> int | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    suffix = text[-1].upper()
    multiplier = 1
    number = text
    if suffix in {"K", "M", "G"}:
        number = text[:-1]
        multiplier = {"K": 1024, "M": 1024**2, "G": 1024**3}[suffix]
    if not number.isdigit():
        raise ValueError("invalid size hint")
    return int(number) * multiplier


def plausible_size(actual: int, hinted: int | None) -> bool:
    if actual <= 0 or actual > MAX_BYTES:
        return False
    if hinted is None or hinted == 0:
        return True
    # Aminet INDEX size is deliberately coarse. Reject only gross mismatches.
    lower = max(1, hinted // 2)
    upper = min(MAX_BYTES, hinted * 2 + 4096)
    return lower <= actual <= upper


def load_mirror_bases(path: Path) -> list[str]:
    bases: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parsed = urllib.parse.urlparse(line)
        if parsed.scheme != "https":
            continue
        if parsed.path.endswith("/INDEX"):
            base_path = parsed.path[: -len("INDEX")]
            bases.append(urllib.parse.urlunparse(parsed._replace(path=base_path)))
        else:
            bases.append(line.rstrip("/") + "/")
    if not bases:
        raise ValueError("no HTTPS Aminet mirrors configured")
    return bases


def artifact_url(base: str, artifact: str) -> str:
    safe_parts = [urllib.parse.quote(part, safe="._-+") for part in artifact.split("/")]
    return base.rstrip("/") + "/" + "/".join(safe_parts)


def download_to_temp(url: str, directory: Path) -> tuple[Path, int]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    temp_path: Path | None = None
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            length = response.headers.get("Content-Length")
            if length is not None and int(length) > MAX_BYTES:
                raise ValueError("remote artifact exceeds safety limit")
            with tempfile.NamedTemporaryFile(dir=directory, delete=False) as tmp:
                temp_path = Path(tmp.name)
                total = 0
                while True:
                    block = response.read(CHUNK)
                    if not block:
                        break
                    total += len(block)
                    if total > MAX_BYTES:
                        raise ValueError("artifact exceeds safety limit")
                    tmp.write(block)
                tmp.flush()
        assert temp_path is not None
        return temp_path, total
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def fetch_artifact(artifact: str, output: Path, size_hint: str | None,
                   mirror_config: Path, explicit_url: str | None = None) -> int:
    artifact = validate_artifact_path(artifact)
    hinted = parse_size_hint(size_hint)
    output.parent.mkdir(parents=True, exist_ok=True)

    urls = [explicit_url] if explicit_url else [
        artifact_url(base, artifact) for base in load_mirror_bases(mirror_config)
    ]
    errors: list[str] = []

    for url in urls:
        if url is None:
            continue
        try:
            temp_path, total = download_to_temp(url, output.parent)
            if not plausible_size(total, hinted):
                temp_path.unlink(missing_ok=True)
                raise ValueError(
                    f"downloaded size {total} is implausible for INDEX hint {size_hint!r}"
                )
            temp_path.replace(output)
            print(f"AmiGet: staged {artifact} ({total} bytes) from {url}")
            print(f"AmiGet: staging file: {output}")
            return 0
        except (OSError, ValueError, urllib.error.URLError) as exc:
            errors.append(f"{url}: {exc}")

    for error in errors:
        print(error)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", help="canonical Aminet path, e.g. util/libs/Foo.lha")
    parser.add_argument("--output", required=True, help="final staging file")
    parser.add_argument("--size", help="coarse Aminet INDEX size hint, e.g. 34K")
    parser.add_argument("--mirrors", default=str(DEFAULT_MIRRORS))
    parser.add_argument("--url", help="explicit transport URL for qualification/testing")
    args = parser.parse_args()

    try:
        return fetch_artifact(
            args.artifact,
            Path(args.output),
            args.size,
            Path(args.mirrors),
            args.url,
        )
    except (OSError, ValueError) as exc:
        print(f"AmiGet: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
