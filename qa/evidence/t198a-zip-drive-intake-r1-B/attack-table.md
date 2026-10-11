# t198a r1 seat B: attack tables (full data in results/*.json, scripts in scripts/)

## Archive handling: 331 hostile or healthy archives, `expand_zip`, 3 members (a,b,c) each, built by `scripts/zip_attack.py` with a raw zip writer
New tree = 3918a8aa, old tree = 894549ee, same inputs. Old raised on 40 cases; new raises on 1. Staging leftovers: none in any case (new). Files in `sources/` equal rows in every case (no row without file, no file without row).

| input (position first/middle/last each unless noted) | new outcome |
|---|---|
| bit flip at 0/20/50/80/99% in stored, deflate, bzip2, lzma data | `partial`, only the damaged member `failed`, other two registered (lzma flips were 11 raises in old) |
| truncated data (0/40/90% kept), csize consistent or still claiming full, 4 methods | `partial`, damaged member `failed` |
| wrong CRC, stream decodes, 4 methods | `partial`, member `failed` |
| lzma header oddities: bad props, psize 0 / 65535, 3-byte and 5-byte data, garbage, empty | `partial`, member `failed` (bad props, psize 0 and zeros were raises in old) |
| deflate/bzip2/lzma garbage, empty, zeros | `partial`, member `failed` (bzip2 noise/zeros gives reason "could not be staged (the write failed)": wrong wording, still failed) |
| unknown method ids 1,6,9,10,18,19,20,93-99,255,65535 | `partial`, member `failed` "unsupported compression method" |
| flags: encrypted, enc+masked, enc+strong, patched 0x20, strong 0x40, masked 0x2000; encrypted in central only | `partial`, member `failed` |
| extract_version 20 and 63 (any position, either header) | `ok`, 3 registered (same as old) |
| extract_version 64/99/255/65535 in the CENTRAL header, first/middle/last (24 cases) | whole archive `failed`, ONE row `(archive)` "unsupported zip version", exit 2, NOTHING registered (old: NotImplementedError raised). In the local header only: `ok` |
| zip64: healthy forced, extra with wrong sizes | `ok`, 3 registered |
| zip64: extra truncated/empty/truncfield, 0xFFFFFFFF offset | whole archive `failed` "not a zip archive" |
| zip64: huge claimed size | whole archive `failed` (total size limit) |
| central directory: bad signature, cd size wrong, extra-len overflow, no EOCD, truncated CD | whole archive `failed` "not a zip archive" |
| central directory: count high/low, comment length lies | `ok` (stdlib tolerant), 3 registered |
| central directory: offset wrong | all 3 `failed` |
| local offset bad / past EOF / local name differs / csize past EOF / usize lies small | `partial`, member(s) `failed` |
| usize lies big | member `failed` per-file limit |
| NUL byte or name length overflow | member `failed` "control character in name" |
| **flag 0x800 (UTF-8 names) with invalid UTF-8 bytes in a name** | **`UnicodeDecodeError` raised out of `expand_zip`** (same in old; not fixed). Through the upload route it propagates out of `handle_upload` (it catches only UploadRefused, IntakeBusy, OSError): `results/utf8-name-route.txt`; archive in `results/cd-utf8-flag-bad-name.zip` (387 bytes) |
| not-a-zip text, empty file | `failed`, one row |
| random fuzz: 2,500 mutations of 1-3 bytes (biased to headers) over healthy stored/deflate/bzip2/lzma archives (`scripts/fuzz.py`) | 0 exceptions: 1,802 partial, 385 ok, 313 failed |

Healthy archives (stored, deflate, bzip2, lzma, zip64 forced, version 63): old and new produce the same status, the same member rows and the same sha256 per row (`results/zip-old-vs-new.txt`: all 39 changed cases are cases old raised on).

## Field caps: 29 upload-route cases (`scripts/http_attack.py`, ASGI level, tracemalloc peak, limit 1-16 MiB per case)
| input | status | bytes pulled | peak MiB | file bytes written / rows / staging |
|---|---|---|---|---|
| 9 distinct small fields before file / after the file | 400 too many fields | 5.6 KB | 0.13 | none / 0 / empty |
| 8 distinct fields then file | 303 (allowed) | | | 1 row |
| same name 20,000 times (before file; after file) | 400 total cap, after 458 KB | 0.29 | none / 0 / empty |
| 150,000 distinct fields (17 MB body): OLD 894549ee | 303, whole body read | 17.0 MB | 25.85 | 1 row |
| same input, NEW | 400 too many fields | 65 KB (first chunk) | 0.96 | none / 0 / empty |
| file part without filename (50x "recording") | 303 (counted as fields, small) | | | |
| name 7,900 B x5 / name 9,000 B | 400 (library header cap) | 44 KB / 14 KB | 0.2 | none |
| single value 16,384 / 16,385 B | 303 / 400 | | | |
| two values of 16,384 B | 400 total cap | 38 KB | 0.23 | none |
| 16,384 + 16,368 + 1 B (just under total) / 16,384 + 16,300 | 303 | | | 1 row |
| endless single field value | 400 at 65 KB | | 0.24 | none |
| many distinct headers in one part (4/8/16 MiB), also in the file part | 400 "could not be read as a form" after the first 64 KB: python-multipart 0.0.32 raises `Maximum header count exceeded` (a library default; uv.lock pins 0.0.32, pyproject says `>=0.0.32`) | 64 KB | 0.25 | none |
| 8 MiB of empty parts with no headers | 303 | whole 8.4 MB | 0.29 | 1 row; not retained, bounded by the body limit |
| 200,000 empty-named fields, limit 2 MiB | 413 at the body limit | 2.4 MB | 1.0 | none |
| 1-byte chunks, 7-byte chunks (boundary split) valid with label | 303, same as one chunk | | | 1 row |
| 1-byte chunks with 9 fields | 400, same as one chunk | 652 B | 0.12 | none |
| filename with no content | 400 empty | | | none |

Refused requests left no file bytes under `sources/`, no row, and only an empty `.work/uploads/demo` directory (the per-request folder is removed in `finally`).
