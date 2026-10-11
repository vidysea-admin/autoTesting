# Falsification (one per repaired criterion, throwaway copy of the tree, copy imports its own src)

Green = the named tests on the unmutated copy. Red = same tests after the mutation. Copy deleted after.

| TV10-storage A1 review_scratch finally-rmtree removed | successful_redacted_run or ctrl_c or provider_error_midway or spend_cap_stop | copy imports falsify/row0/src/autotester/__init__.py | green: rc=0 ....                                                                     [100%]
 | red: rc=1 FAILED tests/test_video_review_cleanup.py::test_a_provider_error_midway_leaves_only_the_stored_review |
| TV10-storage A2 .gitignore reviews line removed | gitignored_in_the_real_repo | copy imports falsify/row1/src/autotester/__init__.py | green: rc=0 ........                                                                 [100%]
 | red: rc=1 .py::test_the_stored_review_and_its_exports_are_gitignored_in_the_real_repo[md]
FAILED tests/test_video_review_cleanup.py::test_the_stored_review_and_its_exports_are_gitignored_in_the_real_repo[html]
 |
| TV7.4 cap B1 CLI isfinite check removed | non_finite_or_negative_spend_cap | copy imports falsify/row2/src/autotester/__init__.py | green: rc=0 .....                                                                    [100%]
 | red: rc=1 FAILED tests/test_cli_video_review_exits.py::test_a_non_finite_or_negative_spend_cap_is_a_usage_error_not_no_cap[NaN] |
| TV7.4 cap B2 batch loop NaN-safe compare reverted | batch_loop_itself_stops_on_a_nan_cap | copy imports falsify/row3/src/autotester/__init__.py | green: rc=0 .                                                                        [100%]
 | red: rc=1 iew_gates.py:277: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_video_review_gates.py::test_the_batch_loop_itself_stops_on_a_nan_cap
 |
| JSON C1 _fail no longer prints the document | every_exit_path | copy imports falsify/row4/src/autotester/__init__.py | green: rc=0 ..............                                                           [100%]
 | red: rc=1 _exit_path_writes_exactly_one_json_document_to_stdout[dry-run-bad-redact-1]
FAILED tests/test_cli_video_review_exits.py::test_every_exit_path_writes_exactly_one_json_document_to_stdout[no-approval-3]
 |
| Pointer limits D1 line limit off by one | size_limits | copy imports falsify/row5/src/autotester/__init__.py | green: rc=0 .                                                                        [100%]
 | red: rc=1 FAILED tests/test_video_pointers.py::test_pointer_size_limits_are_errors_never_truncation |
| Pointer limits D2 file-size limit off by one | size_limits | copy imports falsify/row6/src/autotester/__init__.py | green: rc=0 .                                                                        [100%]
 | red: rc=0 .                                                                        [100%]
 |

Surviving mutant D2 (file-size limit off by one, `size > MAX_POINTER_FILE_BYTES + 1`): tests/test_video_pointers.py + tests/test_cli_video_review_exits.py + tests/test_video_review.py = 83 passed. The repo suite never tests the 32769-byte boundary; my behavioural run does and HEAD is correct (32768 accepted, 32769 refused). Observation only.
