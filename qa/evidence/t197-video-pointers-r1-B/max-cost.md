# --max-cost values, text and json modes (each row: real CLI, wm provider)

| value | mode | rc | calls | one JSON doc | status | exit_code key |
|---|---|---|---|---|---|---|
| 'nan' | text | 1 | 0 | False | None | n/a |
| 'nan' | json | 1 | 0 | True | usage_error | 1 |
| 'NaN' | text | 1 | 0 | False | None | n/a |
| 'NaN' | json | 1 | 0 | True | usage_error | 1 |
| 'inf' | text | 1 | 0 | False | None | n/a |
| 'inf' | json | 1 | 0 | True | usage_error | 1 |
| '-inf' | text | 1 | 0 | False | None | n/a |
| '-inf' | json | 1 | 0 | True | usage_error | 1 |
| 'infinity' | text | 1 | 0 | False | None | n/a |
| 'infinity' | json | 1 | 0 | True | usage_error | 1 |
| '-1' | text | 1 | 0 | False | None | n/a |
| '-1' | json | 1 | 0 | True | usage_error | 1 |
| '-0.0001' | text | 1 | 0 | False | None | n/a |
| '-0.0001' | json | 1 | 0 | True | usage_error | 1 |
| '0' | text | 1 | 0 | False | None | n/a |
| '0' | json | 1 | 0 | True | failed | absent |
| '1e-9' | text | 0 | 1 | False | None | n/a |
| '1e-9' | json | 0 | 1 | True | partial | absent |
| '1e30' | text | 0 | 2 | False | None | n/a |
| '1e30' | json | 0 | 2 | True | ok | absent |
| '1e308' | text | 0 | 2 | False | None | n/a |
| '1e308' | json | 0 | 2 | True | ok | absent |
| '1e400' | text | 1 | 0 | False | None | n/a |
| '1e400' | json | 1 | 0 | True | usage_error | 1 |
| 'abc' | text | 2 | 0 | False | None | n/a |
| 'abc' | json | 2 | 0 | False | None | n/a |
| '' | text | 2 | 0 | False | None | n/a |
| '' | json | 2 | 0 | False | None | n/a |
| '0x10' | text | 2 | 0 | False | None | n/a |
| '0x10' | json | 2 | 0 | False | None | n/a |
| '1_0' | text | 0 | 2 | False | None | n/a |
| '1_0' | json | 0 | 2 | True | ok | absent |

nan/NaN/inf/-inf/infinity/1e400/negative: exit 1, 0 calls, JSON usage_error with exit_code 1. 0: failed review (0 calls). 1e-9: partial, 1 call. 1e30, 1e308, 1_0: ok, 2 calls.
abc, empty, 0x10 (click rejects the float): exit 2, EMPTY stdout in --output json mode (finding F2).
