# M3.4 — Verified staging promotion gate

M3.4 introduces an explicit state transition between cryptographic verification and any future install-planning engine.

Input is an immutable M3.2 verified manifest. The gate requires:

- `format=1`
- `status=verified`
- `install_ready=no`
- positive `size_bytes`
- syntactically valid SHA-256
- the referenced staged file still exists
- the staged file size still matches the verified manifest

On success, AmiGet writes a separate state file atomically with:

- `status=ready-for-plan`
- `install_ready=no`
- artifact path, staged file, byte size and SHA-256 copied from the verified manifest
- a reference to the verified source manifest

This milestone deliberately does **not** unpack archives, inspect install recipes, modify AmigaOS assigns, copy files into system locations, execute Installer scripts, or set `install_ready=yes`.

The state file is a capability boundary: later planning code may consume `ready-for-plan`, while unverified/download-only artifacts must be rejected.

Qualification is host-side and deterministic via `tools/check_m3_4.py`. Runtime installation is not claimed.
