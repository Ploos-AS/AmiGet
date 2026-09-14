# M4.3 — Safe staging extraction

M4.3 introduces the first extraction step in AmiGet's install pipeline. It does **not** install files into AmigaOS assigns or modify the target system. Archive contents are extracted only into a caller-selected staging directory.

## Scope

The reference extractor is `tools/extract_lha_staging.py`.

For this milestone it deliberately supports only classic level-0 LhA headers using the uncompressed `-lh0-` method. Compressed methods such as `-lh5-` remain fail-closed until a decoder path is selected and separately qualified.

The staged extraction path is:

1. parse and validate every archive header;
2. revalidate every member path;
3. enforce per-member, total-size and entry-count limits;
4. extract into a temporary sibling directory;
5. reject duplicate paths and any existing final staging destination;
6. atomically promote the temporary tree to the requested staging path;
7. write extraction state with `install_ready=no`.

No M4.3 operation writes to `SYS:`, `C:`, `LIBS:`, `DEVS:`, `S:` or any other Amiga assign.

## State contract

Successful extraction writes a state file containing at least:

```text
format=1
archive=<source archive>
staging=<staging directory>
member_count=<n>
member.N=<path>|-lh0-|<size>
status=extracted-staging
extract_ready=yes
install_ready=no
```

`extract_ready=yes` means only that a validated staging tree exists. It must not be interpreted as permission to install it.

## Safety properties

M4.3 must fail closed for:

- absolute paths, Amiga assign paths and `..` traversal;
- unsupported LhA header levels;
- compressed methods not explicitly qualified;
- malformed/truncated headers or payloads;
- duplicate archive member paths;
- excessive member count or extracted size;
- an already-existing final staging directory.

Failed extraction must not replace an existing staging tree or promote a partial temporary tree.

## Qualification

Run:

```sh
make check-m4_3
```

The qualification gate validates successful `-lh0-` staging plus refusal of traversal, existing-destination overwrite, unsupported compression and duplicate members.

## Explicitly out of scope

M4.3 does not yet implement:

- installation to Amiga assigns;
- rollback of installed files;
- ownership/receipt database updates;
- compressed LhA extraction;
- execution of Installer scripts or package hooks.

Those remain later M4/M5 work. The next install-engine step should consume a qualified staging tree and produce a dry-run transaction against declared destinations before any live filesystem mutation is allowed.
