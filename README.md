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

## Planned command model

The exact CLI is not frozen yet, but the intended user experience is:

```text
AmiGet update
AmiGet search <term>
AmiGet info <package>
AmiGet install <package>
AmiGet remove <package>
AmiGet upgrade
AmiGet doctor
AmiGet profile install <profile>
```

## Repository layout

```text
src/                 Amiga client source code
include/             Public/internal headers
packages/            AmiGet package metadata
profiles/            Curated package profiles
docs/                Design and milestone documentation
tools/               Host-side validation/development tools
```

## Milestones

- **M0 — Foundation:** repository structure, scope, metadata format draft and validation gate.
- **M1 — Local catalogue:** parse local package metadata; implement list/search/info without networking or installation.
- **M2 — Aminet index:** fetch/update catalogue data and map packages to upstream Aminet artifacts.
- **M3 — Download + verification:** retrieve archives safely and verify integrity.
- **M4 — Install engine:** unpack and install packages with explicit recipes and dry-run support.
- **M5 — Dependencies + state:** dependency resolution, installed-package database and removal support.
- **M6 — Profiles:** curated bootstrap profiles such as base/networking/development/BBS/security.
- **M7 — Upgrade/doctor:** package upgrades, consistency checks and repair guidance.
- **M8 — Integration:** ARexx and integration hooks for other Ploos-AS Amiga tools.
- **M9 — Release qualification:** classic-hardware/emulator qualification and release packaging.

See [docs/ROADMAP.md](docs/ROADMAP.md) for details.

## M0 status

M0 defines the project contract and repository baseline. It intentionally does **not** download or install software yet.

Run the host-side gate with:

```sh
python3 tools/check_m0.py
```

Expected result:

```text
M0 PASS
```

## License

MIT. See [LICENSE](LICENSE).

Copyright (c) 2026 Ploos AS.
