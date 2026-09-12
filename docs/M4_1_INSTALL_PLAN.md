# M4.1 — install plan generator

M4.1 adds deterministic planning after M3.4 promotion. It still performs no installation.

Inputs:

1. Curated package metadata (`.pkg`).
2. M3.4 `ready-for-plan` state.
3. A declarative install recipe selected by `install_recipe`.

The generator verifies that the promoted artifact path and SHA-256 still match the curated package metadata before any plan is written.

Supported recipe actions in format 1:

- `mkdir|DEST`
- `copy|SOURCE|DEST`
- `assign|NAME|DEST`

Arbitrary command execution, delete operations, Installer scripts, Startup-Sequence edits, wildcards and implicit archive behavior are rejected in M4.1.

Output is an atomic text plan with ordered actions and:

```text
status=planned
install_ready=no
```

The plan is advisory/stateful input for later milestones. M4.1 does not unpack the LhA archive, inspect archive contents, copy files, create assigns, or modify an AmigaOS installation.

Qualification requires deterministic action ordering, package/state SHA-256 binding, rejection of unsupported actions, and preservation of an existing plan when generation fails.
