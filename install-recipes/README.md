# AmiGet install recipes

M4.1 introduces a deliberately small declarative recipe format. Recipes describe a plan only; they are not executable shell scripts.

Format 1 supports only these actions:

```text
format=1
recipe=example
action=mkdir|SYS:Example
action=copy|bin/example|C:Example
action=assign|EXAMPLE|SYS:Example
```

Rules:

- `mkdir|DEST` creates a planned directory action.
- `copy|SOURCE|DEST` plans copying a relative unpacked source path to an AmigaOS destination.
- `assign|NAME|DEST` plans an AmigaDOS assign.
- Arbitrary commands, scripts, deletes, startup-sequence edits, installer execution, wildcards, and implicit archive behavior are not supported in M4.1.
- A package recipe is selected only by its curated `install_recipe` identifier.
- The generator still outputs `install_ready=no`; execution is a later milestone.
