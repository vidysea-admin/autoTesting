# Checkpoint - at1368-env-roundtrip (coordinator B)

Environment fingerprint: Windows 11, Python 3.11.15 (worktree .venv), python-dotenv 1.2.2, uv.lock blob 2d9b39719635. Checked state: a735bc57 (code d39837eb), clean tree. Attribution: checker-B (claude-sonnet-subagent), evidence under D:/autoTesting/.work/tmp/chkB/.

Code hashes (blob): core/env.py 636a715f68dd · ui/env_editor.py a0d47cf9865a · core/redact_cli.py 4ba4f0cc1cd4 · providers/litellm_provider.py 0de3f889d319 · core/image_privacy.py 6dfd99031421 · tests/test_env_loading.py dc4a0c776f3b · tests/test_ui_credential_safety_project.py e72ecac6b7e8.

| Check | Command / scope | Result |
|---|---|---|
| C1/C2 affected set | uv run pytest tests/test_env_loading.py tests/test_ui_env_editor.py tests/test_ui_settings.py tests/test_server_settings.py tests/test_container_redaction.py tests/test_image_privacy.py (collected 173) | 171 passed, 2 skipped |
| Missed candidates | 10 files: approval_prod_gate, ui_auth_envkeys, litellm_guard, litellm_provider, browser_use_pin_telemetry, role_onboarding, ui_credential_safety_project, failure_bundle, role_port_authz, real_acceptance (collected 170) | 169 passed, 1 FAILED test_ui_credential_safety_project.py::test_a_value_that_cannot_round_trip_is_refused_not_mangled |
| Other set_env_value users | test_core, test_schedule_tick, test_ui_auth_host_and_consent, test_ui_auth_surface, test_ui_origin_guard, test_ui_project_intake (209) | 209 passed |
| Baseline of the red node | git archive 83e8f71e copy, same node | 1 passed |
| Writer fuzz | fuzz_rt.py, seed 1368, 1,568,598 values + 4,000 on-disk with neighbours | 0 altered, 0 load mismatch |
| Old vs new reading | diff_read.py, 74,241 files | 188 differ, all contain `${`; 0 otherwise |
| Old vs new writer | diff_old.py / rate2.py | refused old 2.46 %, new 0.47 %, newly refused 0.07 % |
| Redaction | redact.py, 12 values | all masked as typed |
| Falsification | copies row1 (interpolate True), row2 (old writer), row3 (loader leg dropped); green-before then red-after | red in all three on the property test |

Remaining: none. Verdict: FAIL (C2, P1).
