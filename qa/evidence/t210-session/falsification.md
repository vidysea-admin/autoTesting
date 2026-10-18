# Falsification evidence - t210-session cycle 0 (checker, copies of git archive 42fc8dc9 outside the worktree)

Run: PYTHONPATH=<copy>/src <worktree>/.venv python -m pytest <named nodes> -p no:cacheprovider; autotester.__file__ confirmed inside each copy.

## row-a green before
2 passed, 1 warning in 7.96s
## row-a red after
>           raise ValueError("two role accounts resolved to the same profile directory")
E           ValueError: two role accounts resolved to the same profile directory
src\autotester\stages\multi_role_session.py:104: ValueError
>           raise ValueError("two role accounts resolved to the same profile directory")
E           ValueError: two role accounts resolved to the same profile directory
src\autotester\stages\multi_role_session.py:104: ValueError
FAILED tests/test_multi_role_session.py::test_one_session_and_one_distinct_profile_dir_per_account
FAILED tests/test_multi_role_session.py::test_mp11_contexts_share_no_cookies_storage_or_profile_and_signout_is_local
2 failed, 1 warning in 1.91s

## row-a2 green before
2 passed, 1 warning in 7.95s
## row-a2 red after
E           AssertionError: assert (3 == 3 and 1 == 3)
tests\test_multi_role_session.py:86: AssertionError
E           AssertionError: assert (WindowsPath('C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/e46c0e51-15e9-4a31-a0b0-cf49de9d445f/scratchpad/row-a2/.work/pytest-tmp/r27716-1792355452/test_mp11_contexts_share_no_co0/profiles/t210-role') != WindowsP
tests\test_multi_role_session.py:215: AssertionError
FAILED tests/test_multi_role_session.py::test_one_session_and_one_distinct_profile_dir_per_account
FAILED tests/test_multi_role_session.py::test_mp11_contexts_share_no_cookies_storage_or_profile_and_signout_is_local
2 failed, 1 warning in 10.46s

## row-b green before
8 passed, 1 warning in 11.16s
## row-b red after
E       AssertionError: assert (<LinkStatus.FAILED: 'failed'> is <LinkStatus.FAILED: 'failed'> and None == 'evil.example.test')
tests\test_platform_links.py:66: AssertionError
E       AssertionError: assert (<LinkStatus.FOLLOWED: 'followed'> is <LinkStatus.FAILED: 'failed'>)
tests\test_platform_links.py:66: AssertionError
tests\test_platform_links.py:208: AssertionError
FAILED tests/test_platform_links.py::test_judge_hops_matrix[off_platform_direct]
FAILED tests/test_platform_links.py::test_judge_hops_matrix[off_platform_mid_chain]
FAILED tests/test_platform_links.py::test_mp12_fixture_links_redirect_sso_control_off_platform_chain_404_and_unreached
3 failed, 5 passed, 1 warning in 11.70s

Edits: a = multi_role_session.py:79 profile slug f"{project.slug}-role-{aid}" -> f"{project.slug}-role" (manifest's mutant; red on the open() guard ValueError at :104). a2 = the same plus :103 guard -> if False (guard bypassed; red on the named assertions: 3 sessions but 1 distinct profile dir, profiles[0] != profiles[1]). b = platform_links.py judge_hops off-platform host test -> if False (red on test_judge_hops_matrix[off_platform_direct], [off_platform_mid_chain] and the live 7-link test).
