# AmiGet Roadmap

## Design principles

AmiGet is a package-management layer for classic AmigaOS. Aminet remains an upstream software archive; AmiGet adds machine-readable metadata, verification, dependency information and predictable installation behaviour.

AmiGet should prefer interoperability over creating another isolated package ecosystem. Package sources and formats should be represented through a common package abstraction so that the CLI, dependency solver, installed-state database and ARexx interface do not depend on a particular backend.

The project should remain useful on low-end classic systems. Features that require substantial host-side infrastructure must not make the basic Amiga client unusable offline or on a 68000-class machine.

ARexx support is a project requirement, not an optional afterthought. The native CLI core must remain usable when RexxMast is not running, while systems with RexxMast should expose a documented `AMIGET` public port. Common commands should include `VERSION`, `STATUS` and `HELP`, with stable return-code conventions shared with other Ploos-AS Amiga tools. Package operations should become scriptable through ARexx as their CLI equivalents mature.

## M0 — Foundation

Acceptance criteria:

- Repository scope and goals documented.
- MIT license present.
- Source/include/package/profile/docs/tools layout established.
- Draft package metadata schema documented with an example package.
- Initial curated profile format represented by an example.
- ARexx is recorded as a required project interface, while the CLI remains usable without RexxMast.
- Host-side `tools/check_m0.py` validates the baseline.
- No claim that downloading/installing is implemented.

## M1 — Local catalogue

Implement the first native AmiGet executable and local catalogue reader.

Planned commands:

- `AmiGet version`
- `AmiGet list`
- `AmiGet search <term>`
- `AmiGet info <package>`

M1 must work entirely from local metadata. Network access and installation remain out of scope.

## M2 — Aminet index

Add catalogue update/fetch support and map AmiGet metadata to Aminet artifacts. Keep upstream URLs and metadata separate from installation policy.

## M3 — Download and verification

Download package artifacts to a staging area, validate size/checksum where available, reject malformed metadata and avoid installing directly from an unverified transfer.

## M4 — Install engine

Add explicit installation recipes, archive extraction, dry-run, destination validation and failure-safe staging.

## M5 — Dependencies and installed state

Track installed packages and versions, resolve declared dependencies, detect conflicts and support package removal where a safe recipe exists.

## M6 — Profiles

Provide curated bootstrap profiles. Initial candidates:

- base
- networking
- development
- bbs
- security

Profiles are metadata, not hard-coded installer behaviour.

## M7 — Upgrade and doctor

Add upgrade planning and consistency diagnostics. `doctor` should identify missing dependencies, stale metadata and damaged AmiGet state without silently modifying the system.

## M8 — ARexx and integration

Implement and qualify the required `AMIGET` ARexx port. At minimum expose `VERSION`, `STATUS` and `HELP`, plus appropriate equivalents for mature package operations such as `SEARCH`, `INFO`, `UPDATE`, `INSTALL` and profile handling. Document arguments, results and return codes. RexxMast must remain optional for ordinary CLI operation.

Add optional hooks for Ploos-AS tools such as AmiGuard/AmiForensics/AmiInternals without making them mandatory dependencies.

## M9 — Package abstraction and interoperability

Introduce a backend-neutral package abstraction layer. The user-facing CLI, dependency resolver, transaction engine, installed-state database and ARexx API must operate on normalized package records rather than backend-specific structures.

Planned adapters, in priority order:

1. **Aminet/LhA** — existing Aminet artifacts, `.readme` metadata and AmiGet installation recipes.
2. **AmigaPKG/amipkg** — investigate and implement practical interoperability with the current AmigaPKG repository/recipe ecosystem without needlessly duplicating its metadata.
3. **APS `.aps`** — document the historical Amiga Packaging System and support its package format where technically practical and useful.

The same high-level operations should be usable regardless of backend: `SEARCH`, `INFO`, `INSTALL`, `REMOVE`, `UPDATE`, `UPGRADE`, `VERIFY`, `LIST` and `STATUS` as each operation matures.

Acceptance criteria:

- Backend-neutral package/provider interface documented.
- Aminet/LhA adapter implemented as the reference provider.
- AmigaPKG format/repository compatibility study completed before implementation is frozen.
- APS/apkg historical design and `.aps` format documented and tested against available examples.
- Package identity, versions, dependencies, conflicts, checksums, install/remove behaviour and source provenance have normalized representations.
- Installed-state records retain the originating backend/provider.
- ARexx commands do not expose unnecessary backend-specific behaviour.

## M10 — Native package format decision gate

Do **not** create a fourth package format by default. First evaluate whether Aminet/LhA recipes, AmigaPKG and APS can represent AmiGet's requirements.

Research requirements include:

- self-describing package metadata;
- dependency/conflict/provides semantics;
- CPU and AmigaOS requirements;
- checksums and package/repository signatures;
- deterministic install/remove and file ownership;
- upgrade and rollback support;
- pre/post install/remove hooks with explicit safety policy;
- ARexx-related metadata/hooks where useful;
- operation on low-end classic systems;
- ability to inspect/extract packages with conventional Amiga tools where practical.

A native AmiGet package format may proceed only when this investigation identifies concrete requirements that cannot reasonably be satisfied through interoperability or compatible extensions. If required, specify the smallest possible format and prefer an Amiga-friendly existing archive container such as LhA.

The historical name `apkg` must not be reused casually: APS already used `apkg` for its low-level package engine. Any reuse must be an intentional compatibility/revival decision rather than an unrelated new format.

Decision output:

- **No native format:** AmiGet remains a universal package-management layer over the supported ecosystems; or
- **Native format justified:** publish a versioned format specification, compatibility rationale and migration/interoperability plan before implementation.

## M11 — Release qualification

Qualify supported AmigaOS/CPU profiles under emulation and selected real hardware. ARexx qualification is part of the supported runtime matrix when RexxMast is available. Interoperability providers included in a release must have provider-specific regression tests in addition to backend-neutral transaction tests. Produce reproducible release archives and installation documentation.
