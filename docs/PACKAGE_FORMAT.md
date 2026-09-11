# AmiGet package metadata — draft v0

This format is deliberately small for M0. It is expected to evolve before a stable AmiGet release.

Package metadata is stored as simple `key=value` text so that it can be parsed on classic AmigaOS without requiring a JSON library.

Example:

```text
format=0
name=lha
version=example
summary=LhA archive utility
source=aminet
aminet_path=util/arc/example.lha
os_min=2.04
cpu_min=68000
archive=lha
sha256=UNSET
install_recipe=manual
```

## Required M0 keys

- `format`: metadata format version; currently `0`.
- `name`: lowercase AmiGet package identifier.
- `version`: upstream version or an explicit placeholder in example data.
- `summary`: short human-readable description.
- `source`: upstream source identifier; M0 uses `aminet`.
- `aminet_path`: relative Aminet artifact path.
- `os_min`: minimum intended AmigaOS version.
- `cpu_min`: minimum CPU family.
- `archive`: archive/container type.
- `sha256`: expected SHA-256 or `UNSET` while metadata is only illustrative.
- `install_recipe`: installation policy identifier.

## Safety rules

Production package metadata must never treat an absent checksum as a successful verification. `UNSET` is permitted only for development/example records until a later milestone defines the trust and verification policy.

Installation recipes must be explicit. AmiGet should not infer arbitrary shell commands from archive contents.

Aminet paths are upstream references; they are not permission to overwrite system files without an install plan and validation.

## Dependencies

Dependency syntax is deferred until M5. M0/M1 metadata should not pretend dependency resolution exists.
