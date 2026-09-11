# M3.3 Curated package staging

M3.3 binds AmiGet's curated package recipes to the already qualified M3.1 download staging and M3.2 SHA-256 verification layers.

## Trust model

The curated `.pkg` recipe is authoritative for:

- package name/version
- `source=aminet`
- canonical `aminet_path`
- expected SHA-256
- reserved install recipe identifier

The Aminet INDEX remains discovery metadata only. Its size field may be used as an optional coarse sanity hint but is not an integrity mechanism.

## Pipeline

`tools/stage_curated_package.py` performs:

1. parse and validate the curated package recipe;
2. reject unsupported sources, unsafe paths, unsafe package names, missing fields, and non-cryptographic/`UNSET` SHA-256 values;
3. stage the artifact using the M3.1 transport helper;
4. verify the complete staged artifact using M3.2 SHA-256 verification;
5. atomically publish a verified manifest only after the digest matches.

The resulting manifest keeps `install_ready=no`. M3.3 does not unpack, execute, or install anything.

## Failure behaviour

- download/size failure: no verified manifest is published;
- checksum mismatch: staged bytes may remain for diagnosis, but no verified manifest is published;
- existing verified manifests are only replaced by another successful verification;
- `sha256=UNSET` is rejected.

## Qualification

`python3 tools/check_m3_3.py` uses a deterministic local artifact URL and validates both the success path and fail-closed checksum behaviour.
