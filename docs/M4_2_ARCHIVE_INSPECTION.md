# M4.2 — LhA archive inspection and plan/source binding

M4.2 adds a pre-extraction safety gate. AmiGet can inspect a staged LhA archive, create a deterministic inventory, and verify that every `copy` source named by an M4.1 install plan exists in that inventory.

## Safety boundary

M4.2 does **not** extract or install anything. A successful result still records:

```text
extract_ready=no
install_ready=no
```

The archive inspector rejects absolute paths, `..` traversal, Amiga-style `:` paths inside the archive, truncated members, excessive member sizes/counts, and unsupported header levels.

## LhA support in M4.2

The built-in inspector deliberately supports only classic **level-0 LhA headers**. Other header levels fail closed. This keeps the first archive parser small and deterministic enough to qualify without depending on a host `lha`, `7z`, or other external extraction utility.

Later milestones can extend the parser to additional LhA header levels after dedicated fixtures and qualification exist.

## Inventory

`tools/inspect_lha_archive.py` writes a key/value inventory containing each member's canonical path, compression method marker, packed size, and original size.

Example:

```text
format=1
archive=staging/sample.lha
member_count=2
member.1=C/sample|-lh0-|123|123
member.2=Libs/sample.library|-lh0-|456|456
status=inspected
extract_ready=no
```

## Plan binding

`tools/bind_plan_sources.py` consumes an M4.1 plan and an inspected inventory. Every `copy|source|destination` source must match an inventory member exactly. Missing or unsafe sources reject the binding transaction.

A successful bound state has:

```text
status=sources-validated
extract_ready=no
install_ready=no
```

This is still only evidence that planned sources exist in the archive. It is not permission to extract or write AmigaOS files.
