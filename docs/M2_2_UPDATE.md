# M2.2 — Native cache update

M2.2 moves Aminet cache replacement into the native `AmiGet` executable while keeping network transport separate from the catalogue parser.

## Command

```text
AmiGet update <INDEX> [cache]
```

The default cache path is `cache/aminet.cache`.

`update` parses the supplied Aminet `INDEX` into a temporary `<cache>.new` file and only renames it into place after a usable catalogue has been produced. A failed parse/build must not modify an existing cache.

## Transport boundary

`AmiGet update` does not itself assume AmiTCP, Roadshow, Miami, curl, wget, or a TLS implementation. Transport obtains an `INDEX`; the native core validates, parses and commits it.

For host development, `tools/fetch_aminet_index.py` reads `config/mirrors.conf`, tries HTTPS mirrors in order, validates a size/content envelope and writes the downloaded INDEX atomically.

A later Amiga transport adapter may use the same mirror configuration and hand the downloaded file to the same native update path. This avoids coupling catalogue semantics to one TCP/IP stack.

## Safety properties

- Existing cache is preserved when INDEX parsing fails.
- Temporary cache is removed on parse/build failure.
- Empty/unusable INDEX data is rejected.
- Mirror configuration accepts HTTPS URLs only in the host helper.
- Package installation remains out of scope.

## Qualification

`tools/check_m2_2.py` verifies:

- version marker `0.2.0-m2.2`;
- successful native cache creation from the fixture INDEX;
- rejection of malformed INDEX input;
- preservation of an existing cache after a failed update;
- cleanup of a failed temporary cache;
- presence of fallback HTTPS mirrors.
