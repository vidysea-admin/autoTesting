# Pointer-file limits at and one over each boundary (dry-run and full run)

| case | bytes | expect | dry rc | dry status | errors | first error | run rc | run calls | run one JSON |
|---|---|---|---|---|---|---|---|---|---|
| 100 lines LF | 1090 | accepted | 0 | plan | 0 | None | 0 | 2 | True |
| 101 lines LF | 1102 | refused | 2 | pointer_errors | 1 | too many pointer lines (max 100) | 2 | 0 | True |
| 100 lines CRLF+BOM | 1193 | accepted | 0 | plan | 0 | None | 0 | 2 | True |
| 101 lines CRLF+BOM | 1206 | refused | 2 | pointer_errors | 1 | too many pointer lines (max 100) | 2 | 0 | True |
| 100 non-blank + 50 blank lines | 550 | accepted | 0 | plan | 0 | None | 0 | 2 | True |
| note 500 chars | 508 | accepted | 0 | plan | 0 | None | 0 | 2 | True |
| note 501 chars | 509 | refused | 2 | pointer_errors | 1 | note is 501 characters (max 500) | 2 | 0 | True |
| note 500 chars CRLF+BOM | 512 | accepted | 0 | plan | 0 | None | 0 | 2 | True |
| note 501 chars CRLF+BOM | 513 | refused | 2 | pointer_errors | 1 | note is 501 characters (max 500) | 2 | 0 | True |
| note 500 multibyte chars (1000 B) | 1008 | accepted | 0 | plan | 0 | None | 0 | 2 | True |
| note 501 multibyte chars | 1010 | refused | 2 | pointer_errors | 1 | note is 501 characters (max 500) | 2 | 0 | True |
| free pointer 500 chars | 501 | accepted | 0 | plan | 0 | None | 0 | 2 | True |
| free pointer 501 chars | 502 | refused | 2 | pointer_errors | 1 | note is 501 characters (max 500) | 2 | 0 | True |
| note 500 chars + trailing spaces | 511 | accepted | 0 | plan | 0 | None | 0 | 2 | True |
| 32768 B LF | 32768 | accepted | 0 | plan | 0 | None | 0 | 2 | True |
| 32769 B LF | 32769 | refused | 2 | pointer_errors | 1 | pointer file is 32769 bytes, over the 32768 byte limit | 2 | 0 | True |
| 32768 B CRLF+BOM | 32768 | accepted | 0 | plan | 0 | None | 0 | 2 | True |
| 32769 B CRLF+BOM | 32769 | refused | 2 | pointer_errors | 1 | pointer file is 32769 bytes, over the 32768 byte limit | 2 | 0 | True |
| 10 MiB of blank lines | 10485770 | refused | 2 | pointer_errors | 1 | pointer file is 10485770 bytes, over the 32768 byte limit | 2 | 0 | True |
| empty file | 0 | accepted | 0 | plan | 0 | None | 0 | 2 | True |
