ev-C notes: _sign_in only in asgi_helpers.post_stream (POST only, ASGI path); skipped when AUTOTESTER_TEST_NO_AUTO_LOGIN=1 or no AUTOTESTER_ROOT/AUTH_DIR; no per-call opt-out arg.
au16 (tests/test_ui_auth_surface.py:48) walks all app routes unauthenticated (auth_harness.gate_on sets NO_AUTO_LOGIN=1): JSON->401, HTML->302.
green 8 passed; falsified drive row -> au14 red (1 failed, 7 passed); restored 8 passed. au16 stays green (default deny).
