# M2 — Aminet INDEX ingestion

## Purpose

M2 adds a stack-independent way to ingest the public Aminet `INDEX` file and turn it into a compact local cache suitable for catalogue search.

Aminet currently publishes both `INDEX` and `INDEX.gz` from its mirrors. The parser is deliberately separated from network transport so the classic Amiga client is not coupled to one TLS library or TCP/IP stack.

## Data flow

```text
Aminet mirror
    |
    | HTTPS transport (host helper in M2)
    v
raw INDEX
    |
    | src/aminet_index.c
    v
compact tab-separated cache
    |
    +--> search by name
    +--> search by directory
    +--> search by description
```

## INDEX model

For M2, AmiGet consumes entries shaped as:

```text
<name> <directory> <size> <age> <description...>
```

Whitespace separates the first four fields; the remainder of the line is the description.

The parser intentionally ignores blank/comment/malformed lines rather than trying to interpret arbitrary text as package metadata.

## Cache format

The generated cache contains exactly five tab-separated fields:

```text
name<TAB>directory<TAB>size<TAB>age<TAB>description
```

This is an upstream discovery cache only. It is **not** the trusted AmiGet package recipe database. An Aminet INDEX hit does not authorize installation or overwriting system files.

## Transport

`tools/fetch_aminet_index.py` is an M2 host-side transport helper. It:

- uses HTTPS;
- has a bounded maximum response size;
- validates that the response resembles an Aminet index;
- writes atomically;
- tries a small mirror list unless an explicit URL is supplied.

The classic Amiga transport remains a separate future qualification item. This avoids silently depending on a particular bsdsocket/AmiSSL combination.

## Development CLI

Build the M2 helper:

```sh
make AmiGetIndex
```

Convert a local INDEX:

```sh
./AmiGetIndex build INDEX aminet.cache
```

Search the cache:

```sh
./AmiGetIndex search aminet.cache ssl
```

Host-side live fetch for development:

```sh
python3 tools/fetch_aminet_index.py --output build/aminet/INDEX
./AmiGetIndex build build/aminet/INDEX build/aminet/aminet.cache
```

## Qualification boundary

M2 proves deterministic parsing/cache/search against a fixture. It does not yet claim:

- native Amiga HTTPS fetching;
- package download;
- checksum verification;
- dependency resolution;
- installation.

Those remain later milestones.

## Naming note

There are pre-existing Aminet programs named `amiget`/`Amiget`. This repository therefore carries a naming-collision risk that must be resolved before a public release or Aminet upload.
