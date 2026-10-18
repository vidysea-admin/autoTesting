# T-209 coordinator B - raw results (checker-run)

Scripts in this directory were run with the worktree venv python (`-I`), TMP/TEMP=D:/autoTesting/.work/tmp.

## probe_ids.py (templatise_url on 2000 random ids per format, `https://a.test/students/<id>`)
nanoid21 (base64url)   raw id kept in url_template: 1979/2000 = 99.0%
base62-22              raw id kept in url_template: 1980/2000 = 99.0%
cuid2-24 (a-z0-9)      raw id kept in url_template: 1833/2000 = 91.7%
ULID-26                raw id kept in url_template: 1734/2000 = 86.7%
stripe-like cus_+14    raw id kept in url_template: 1987/2000 = 99.3%
objectid-24 hex        raw id kept in url_template: 0/2000 = 0.0%
uuid4                  raw id kept in url_template: 0/2000 = 0.0%

## probe_leak.py (synthetic rows: fake name/email/phone/secret; fake OCR; synthetic master key; no real .env)
files under run dir: leak/probe-1.png, multi_role_findings/probe-1.json
name/email/phone/phone-tail/master-key/derived-key (hex,b64)/raw row id: absent from run-dir files and log
raw png bytes in any run file: False; log line: `multi-role finding probe-1 class=data_leak count=8`
fake secret `sk-FAKE-SECRET-9f8e7d6c5b4a` placed in the URL PATH: present in run-dir files (url_template kept it verbatim)
templatise https://a.test/invite/xQzLmPwRtYuIoPaSdFgHjK -> unchanged
templatise https://a.test/r/Zk3jQmVxLmPw9RtYu1IoPa5S?x=1 -> path unchanged, query value -> {value}

## render equivalence
render_html(report) sha256[:16] on base 722bf3df src = candidate src = f77b37a13b9ec138 (1649 bytes): no-findings output byte-identical.

## falsification (copies under D:/chk-scratch-t209b/r2/<row>, run_falsify.py; green-before rc=0, red-after rc=1 on the named node)
MP7  PRIVILEGE_ESCALATION P0 -> P1: red test_priority_by_class_over_every_class[privilege_escalation]
MP8  _blocking(findings) -> list(findings) in render_banner: red test_no_banner_without_a_p0_leak_or_privilege_finding
MP9  copyfile(masked) -> copyfile(raw): red test_screenshot_is_masked_before_it_is_written
MP10 write_finding drops last step: red test_replaying_the_recorded_repro_gives_the_same_count
(first attempt rc=4 = conftest needs scripts/regression_proof.py; copies rebuilt with scripts/, runs above are the valid ones)
