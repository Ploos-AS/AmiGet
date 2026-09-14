# M4.4 — Install transaction dry-run

M4.4 turns a qualified M4 install plan plus an M4.3 staging tree into a deterministic transaction description without modifying the target Amiga system.

## Scope

The reference planner validates the extraction state, staging path, staged copy sources and supported install actions. It emits an ordered transaction containing `mkdir` and `copy` operations, with copy sizes accounted for.

No destination assign is opened or modified. No file is copied to `SYS:`, `C:`, `LIBS:` or any other Amiga destination in M4.4.

## Safety properties

- extraction state must be `status=extracted-staging`;
- `extract_ready=yes` and `install_ready=no` are required;
- the recorded staging path must match the supplied staging tree;
- every copy source must exist as a regular staged file;
- source traversal and unsafe Amiga destination paths are rejected;
- duplicate copy destinations are rejected case-insensitively;
- unsupported action types fail closed;
- the transaction is written atomically;
- successful output is `transaction_ready=yes` while `install_ready` remains `no`.

## Qualification

Run:

```sh
make check-m4_4
```

The qualification gate covers a valid transaction, exact byte accounting, missing staged sources, duplicate destinations, destination traversal and extraction-state/staging mismatch.

M4.4 is planning only. A later milestone must introduce an explicit commit/apply gate before AmiGet may mutate the target system.
