# M3.1 — Download staging

M3.1 introduces transport-side artifact download into a staging area. It does **not** install packages.

## Contract

Given a canonical Aminet artifact path such as:

```text
util/libs/AmiSSL-5.19.lha
```

`tools/fetch_aminet_artifact.py`:

1. validates the artifact path before transport,
2. derives candidate artifact URLs from `config/mirrors.conf`,
3. downloads into a temporary file in the destination directory,
4. enforces a hard maximum transfer size,
5. optionally checks the download against the coarse Aminet `INDEX` size hint,
6. atomically replaces the final staging file only after the transfer passes validation.

A failed transfer must not replace an already complete staging file.

## Size semantics

Aminet `INDEX` size values such as `34K` and `4M` are coarse catalogue metadata. M3.1 therefore treats them only as a plausibility check capable of rejecting gross mismatches such as an error page or truncated transfer.

The size hint is **not** an integrity proof and must never be presented as one.

## Security boundary

M3.1 deliberately does not:

- execute the downloaded artifact,
- unpack the archive,
- run Installer scripts,
- copy files into system assigns,
- claim cryptographic verification.

Cryptographic verification and package policy belong to later M3/M4 work.

## Transport boundary

The Python helper is the host/reference transport implementation. The native Amiga client remains independent of a specific TCP/IP/TLS stack. AmiTCP, Roadshow and Miami transport adapters can reuse the same artifact-path and staging contract later.

## Qualification

Run:

```sh
make check
```

M3.1 qualification verifies:

- successful staging from a deterministic local transport source,
- byte-for-byte preservation,
- coarse size mismatch rejection,
- preservation of an existing staging file after failed replacement,
- path traversal rejection,
- temporary-file cleanup,
- mirror fallback configuration.
