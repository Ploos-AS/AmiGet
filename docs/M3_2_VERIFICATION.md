# M3.2 — SHA-256 verification and staged manifest

M3.2 adds a fail-closed verification boundary between download staging and any future installation engine.

## Contract

A staged artifact is not trusted merely because transport completed or its byte count looks plausible. The expected SHA-256 must come from trusted AmiGet package metadata or another trusted verification source.

`tools/verify_staged_artifact.py` hashes the complete staged file and compares it to the expected SHA-256. A successful verification writes a manifest atomically. A mismatch returns failure and does not create or replace a trusted manifest.

Manifest format v1 records:

- canonical artifact path;
- staging file path;
- exact byte size;
- SHA-256 digest;
- `status=verified`;
- `install_ready=no`.

`install_ready=no` is intentional. M3.2 proves artifact identity only; extraction, recipe validation and installation policy remain future milestones.

## Safety properties

- SHA-256 must be exactly 64 hexadecimal characters.
- Artifact paths reject absolute paths and traversal components.
- Verification streams the complete file rather than loading it into memory.
- A failed verification does not overwrite an existing verified manifest.
- A failed verification with no prior manifest creates no manifest.
- Manifest publication is atomic within its destination directory.

## Qualification

Run:

```sh
make check-m3_2
```

The host gate covers successful verification, manifest contents, digest mismatch, preservation of a prior manifest, no-manifest-on-failure, path traversal rejection and malformed digest rejection.
