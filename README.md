# AmiGet

AmiGet is a lightweight package manager and bootstrap tool for classic AmigaOS.

The long-term goal is to make it simple to discover, download, verify and install useful Amiga software, with Aminet as the primary upstream source and a small AmiGet metadata layer for package information, dependencies and installation rules.

## Project goals

- Classic AmigaOS first.
- Target AmigaOS 2.04+ where practical.
- Target 68000 and higher CPUs where practical.
- Keep the client small and usable on real classic hardware.
- Use Aminet as the primary upstream package source rather than replacing it.
- Verify downloads before installation when trustworthy hashes are available.
- Support dependency metadata and reproducible package recipes.
- Support curated profiles such as `base`, `networking`, `development`, `bbs` and `security`.
- Prefer transparent, inspectable package metadata over opaque installers.
- Add ARexx integration where it is useful and technically appropriate.

## Current M1 command model

M1 implements an offline local catalogue only:

```text
AmiGet version
AmiGet list [catalogue]
AmiGet search <term> [catalogue]
AmiGet info <package> [catalogue]
```

The default catalogue is `packages/catalogue.lst`. M1 does **not** perform network access, downloads or installation.

## Build and qualification

Host build:

```sh
make clean
make
```

Run the repository gates:

```sh
make check
```

Expected result includes:

```text
M0 PASS
M1 PASS
```

GitHub Actions runs the same `make check` gate on pushes and pull requests.

## Repository layout

```text
src/                 Amiga client source code
include/             Public/internal headers
packages/            AmiGet package metadata and local catalogue
profiles/            Curated package profiles
docs/                Design and milestone documentation
tools/               Host-side validation/development tools
```

## Milestones

- **M0 — Foundation:** repository structure, scope, metadata format draft and validation gate.
- **M1 — Local catalogue:** native client parses local package metadata and implements version/list/search/info without networking or installation.
- **M2 — Aminet index:** fetch/update catalogue data and map packages to upstream Aminet artifacts.
- **M3 — Download + verification:** retrieve archives safely and verify integrity.
- **M4 — Install engine:** unpack and install packages with explicit recipes and dry-run support.
- **M5 — Dependencies + state:** dependency resolution, installed-package database and removal support.
- **M6 — Profiles:** curated bootstrap profiles such as base/networking/development/BBS/security.
- **M7 — Upgrade/doctor:** package upgrades, consistency checks and repair guidance.
- **M8 — Integration:** ARexx and integration hooks for other Ploos-AS Amiga tools.
- **M9 — Release qualification:** classic-hardware/emulator qualification and release packaging.

See [docs/ROADMAP.md](docs/ROADMAP.md) for details.

## License

MIT. See [LICENSE](LICENSE).

Copyright (c) 2026 Ploos AS.
