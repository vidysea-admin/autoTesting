"""T-212 (multi-role-platform.md MP16, MP17; source-adapters.md SA9): the read-only IMAP reader.

Every test talks to `imap_fake.FakeImap` over a real loopback socket, so the verbs checked are the
ones that crossed the wire, not the ones the reader says it sent. Messages and secrets are
synthetic (MPI2). No real mailbox, no provider call.
"""

from __future__ import annotations

import imaplib
from datetime import UTC, datetime, timedelta

import pytest
from imap_fake import PASSWORD, USER, FakeImap, make_mail

from autotester.schema.mail_observation import (
    CredentialTokenKind,
    MailQuery,
    MailReadResult,
    MailReadState,
    MailUnavailableReason,
)
from autotester.schema.mailbox_ref import MailboxRef
from autotester.sources import imap_mailbox as imap
from autotester.sources.imap_mailbox import read_mailbox

REF = MailboxRef(host_key="QA_IMAP_HOST", user_key="QA_IMAP_USER", password_key="QA_IMAP_PASS")
DECLARED = {"QA_IMAP_HOST", "QA_IMAP_USER", "QA_IMAP_PASS"}
SINCE = datetime(2026, 10, 19, 0, 0, tzinfo=UTC)
FORBIDDEN = {"STORE", "COPY", "MOVE", "EXPUNGE", "APPEND", "DELETE", "SELECT", "CREATE", "RENAME"}


def plain(host: str, port: int, timeout: float) -> imaplib.IMAP4:
    return imaplib.IMAP4(host, port, timeout=timeout)


def creds(server: FakeImap, *, password: str = PASSWORD) -> dict[str, str]:
    return {"QA_IMAP_HOST": server.address, "QA_IMAP_USER": USER, "QA_IMAP_PASS": password}


def query(**kw: object) -> MailQuery:
    recipient = kw.pop("recipient", "role.b@example.test")
    return MailQuery(since=kw.pop("since", SINCE), recipient=recipient, **kw)


def read(server: FakeImap, q: MailQuery | None = None, **kw: object) -> MailReadResult:
    kw.setdefault("connector", plain)
    return read_mailbox(REF, q or query(), kw.pop("credentials", creds(server)),
                        declared_keys=kw.pop("declared_keys", DECLARED), **kw)


# --- MP16: EXAMINE and BODY.PEEK only -------------------------------------------------------
def test_mp16_wire_commands_are_examine_and_peek_only() -> None:
    mails = [make_mail(1, subject="Welcome", body="hello"),
             make_mail(2, subject="Receipt", body="hi")]
    with FakeImap(mails=mails) as server:
        result = read(server)
    assert result.state is MailReadState.READ and len(result.messages) == 2
    verbs = server.verbs()
    assert "EXAMINE" in verbs
    assert not FORBIDDEN & set(verbs), verbs
    fetches = [c for c in server.commands if c.upper().startswith("UID FETCH")]
    assert len(fetches) == 2
    assert all("BODY.PEEK[" in c.upper() and "RFC822" not in c.upper() for c in fetches)
    assert server.seen == set(), "a plain BODY[] fetch would have marked a message read"
    assert set(verbs) <= {"CAPABILITY", "LOGIN", "EXAMINE", "UID", "LOGOUT"}


def test_mp16_the_reader_logs_the_verbs_it_sent_for_the_live_evidence_of_mp34() -> None:
    with FakeImap(mails=[make_mail(1, subject="Welcome", body="hello")]) as server:
        result = read(server)
    assert result.command_log == ["LOGIN", "EXAMINE", "UID SEARCH", "UID FETCH BODY.PEEK", "LOGOUT"]


def test_mp16_a_write_verb_cannot_be_sent_even_by_mistake() -> None:
    session = imap._Session(client=object(), log=[])
    for verb in ("STORE", "COPY", "MOVE", "EXPUNGE", "APPEND", "DELETE", "SELECT", "UID STORE"):
        with pytest.raises(AssertionError):
            session._note(verb)
    assert not [n for n in dir(session) if n.lstrip("_") in {"store", "copy", "expunge", "append"}]


# --- MP17: bounded ----------------------------------------------------------------------------
def test_mp17_message_cap_keeps_the_newest_and_says_it_capped() -> None:
    mails = [make_mail(i, subject=f"Mail {i}", body="x") for i in range(1, 6)]
    with FakeImap(mails=mails) as server:
        result = read(server, query(max_messages=2))
    assert [m.uid for m in result.messages] == [4, 5]
    assert result.capped is True and result.matched_on_server == 5


def test_mp17_recipient_bounds_the_search_and_a_server_that_ignores_it_is_filtered() -> None:
    mails = [make_mail(1, subject="Mine", body="x"),
             make_mail(2, subject="Not mine", body="x", to="someone.else@example.test")]
    with FakeImap(mails=mails, honour_to_filter=False) as server:
        result = read(server)
    assert any('TO' in c and "role.b@example.test" in c for c in server.commands
               if c.upper().startswith("UID SEARCH"))
    assert [m.subject for m in result.messages] == ["Mine"]


def test_mp17_since_time_bounds_the_search_and_older_mail_is_dropped() -> None:
    old = make_mail(1, subject="Old", body="x", sent=SINCE - timedelta(days=3))
    new = make_mail(2, subject="New", body="x", sent=SINCE + timedelta(hours=2))
    with FakeImap(mails=[old, new]) as server:
        result = read(server)
    search = next(c for c in server.commands if c.upper().startswith("UID SEARCH"))
    assert "SINCE 19-Oct-2026" in search
    assert [m.subject for m in result.messages] == ["New"]


def test_mp17_the_connection_is_bounded_by_the_timeout() -> None:
    seen: list[float] = []

    def spy(host: str, port: int, timeout: float) -> imaplib.IMAP4:
        seen.append(timeout)
        return plain(host, port, timeout)

    with FakeImap() as server:
        read(server, query(timeout_s=7.5), connector=spy)
    assert seen == [7.5]


def test_mp17_the_query_refuses_an_unbounded_or_injecting_request() -> None:
    for bad in ({"max_messages": 0}, {"max_messages": 10_000}, {"recipient": 'a b"c'},
                {"recipient": "x@example.test\r\nA1 STORE 1 +FLAGS (\\Deleted)"}):
        with pytest.raises(ValueError):
            query(**bad)
    with pytest.raises(ValueError):
        MailQuery(since=datetime(2026, 10, 19), recipient="a@example.test")   # naive time


# --- MP17: scrubbed, credential-shaped tokens recorded as present, never as values -----------
TOKENS = [
    ("numeric code", "Your verification code is 483920. It expires soon.", "483920",
     CredentialTokenKind.NUMERIC_CODE),
    ("mixed temporary password", "Your temporary password is Xk9#mP2qLw, change it.", "Xk9#mP2qLw",
     CredentialTokenKind.MIXED_TOKEN),
    ("url query token", "Reset here: https://portal.example.test/reset?token=a1B2c3D4e5F6g7&x=1",
     "a1B2c3D4e5F6g7", CredentialTokenKind.URL_TOKEN),
    ("url path token", "Open https://portal.example.test/invite/Zx81Qw93Lm20Pa47Bc56Tr", 
     "Zx81Qw93Lm20Pa47Bc56Tr", CredentialTokenKind.URL_TOKEN),
    ("long standalone token", "Your key: 9fA3kLq82ZxV7mNb4TyUe1WsPd", "9fA3kLq82ZxV7mNb4TyUe1WsPd",
     CredentialTokenKind.MIXED_TOKEN),
]


@pytest.mark.parametrize(("label", "body", "value", "kind"), TOKENS, ids=[t[0] for t in TOKENS])
def test_mp17_each_token_shape_is_recorded_as_present_and_its_value_is_stored_nowhere(
        label: str, body: str, value: str, kind: CredentialTokenKind, tmp_path) -> None:
    with FakeImap(mails=[make_mail(1, subject="Account", body=body)]) as server:
        result = read(server)
    message = result.messages[0]
    assert kind in message.credential_token_kinds and message.credential_token_count >= 1
    out = tmp_path / "mail.json"
    out.write_text(result.model_dump_json(), encoding="utf-8")
    assert value not in out.read_text(encoding="utf-8") and value not in repr(result)


def test_mp17_a_token_in_the_subject_is_masked_and_counted() -> None:
    mail = make_mail(1, subject="Your code is 771204", body="see subject")
    with FakeImap(mails=[mail]) as server:
        result = read(server)
    assert "771204" not in result.messages[0].subject
    assert result.messages[0].credential_token_count == 1


def test_mp17_a_plain_mail_is_not_flagged() -> None:
    body = "Welcome to the portal. Your account is ready. Reference ID 2026 for support."
    with FakeImap(mails=[make_mail(1, subject="Welcome aboard", body=body)]) as server:
        result = read(server)
    assert result.messages[0].credential_token_kinds == []
    assert result.messages[0].credential_token_count == 0


def test_mp17_the_mailbox_password_and_addresses_never_survive_in_a_stored_subject() -> None:
    subject = f"debug {USER} {PASSWORD} from other.person@example.test"
    with FakeImap(mails=[make_mail(1, subject=subject, body="x")]) as server:
        result = read(server)
    dump = result.model_dump_json()
    assert USER not in dump and PASSWORD not in dump       # Redactor.scrub: the mailbox's own keys
    assert "other.person@example.test" not in dump         # mask_pii: an address


# --- SA9: honest failure, never "no message arrived" ---------------------------------------
def test_sa9_a_missing_key_is_unavailable_and_names_only_the_key() -> None:
    with FakeImap() as server:
        partial = {k: v for k, v in creds(server).items() if k != "QA_IMAP_PASS"}
        result = read(server, credentials=partial)
    assert result.state is MailReadState.UNAVAILABLE
    assert result.reason is MailUnavailableReason.KEY_MISSING
    assert result.missing_keys == ["QA_IMAP_PASS"] and server.commands == []


def test_sa9_a_key_the_project_did_not_declare_is_refused_before_any_connection() -> None:
    with FakeImap() as server:
        result = read(server, declared_keys={"QA_IMAP_HOST", "QA_IMAP_USER"})
    assert result.reason is MailUnavailableReason.KEY_UNDECLARED and server.commands == []


def test_sa9_a_refused_login_is_unavailable_and_the_password_is_not_reported() -> None:
    with FakeImap() as server:
        result = read(server, credentials=creds(server, password="wrong-p4ss-canary"))
    assert result.reason is MailUnavailableReason.LOGIN_REFUSED
    dump = result.model_dump_json()
    assert "wrong-p4ss-canary" not in dump and USER not in dump


def test_sa9_an_unreachable_host_is_unavailable_and_the_host_is_not_reported() -> None:
    with FakeImap() as server:
        values = creds(server)
        host = values["QA_IMAP_HOST"]
    values["QA_IMAP_HOST"] = host                      # the server is closed: nothing listens
    result = read_mailbox(REF, query(timeout_s=2), values, declared_keys=DECLARED, connector=plain)
    assert result.reason is MailUnavailableReason.UNREACHABLE
    assert host not in result.model_dump_json()


def test_sa9_a_folder_the_server_refuses_to_examine_is_unavailable() -> None:
    ref = REF.model_copy(update={"folder": "NoSuchFolder"})
    with FakeImap() as server:
        result = read_mailbox(ref, query(), creds(server), declared_keys=DECLARED, connector=plain)
    assert result.reason is MailUnavailableReason.FOLDER_REFUSED
    assert "UID" not in server.verbs()


def test_sa9_an_empty_window_after_a_successful_read_is_a_read_not_unavailable() -> None:
    with FakeImap(mails=[]) as server:
        result = read(server)
    assert result.state is MailReadState.READ and result.messages == [] and not result.capped


# --- SA9: keys by name; values come only from the declared keys of the repo-root .env --------
def test_sa9_only_declared_keys_resolve_and_no_value_reaches_the_run_directory(tmp_path) -> None:
    from autotester.browser.secrets import SecretStore
    from autotester.schema.project import Project, SecretRef
    from autotester.sources.imap_mailbox import credentials_from_store

    env = tmp_path / ".env"
    env.write_text(f"QA_IMAP_HOST=127.0.0.1:1\nQA_IMAP_USER={USER}\nQA_IMAP_PASS={PASSWORD}\n"
                   "OTHER_PROJECT_KEY=other-canary-value\n", encoding="utf-8")
    project = Project(slug="demo", name="Demo", base_url="https://app.example.test",
                      secrets=[SecretRef(key="QA_IMAP_HOST"), SecretRef(key="QA_IMAP_USER")])
    store = SecretStore.load(project, env, strict=False)
    got = credentials_from_store(store, REF)
    assert set(got) == {"QA_IMAP_HOST", "QA_IMAP_USER"}            # the password key is undeclared
    result = read_mailbox(REF, query(), got, declared_keys=set(got), connector=plain)
    assert result.reason is MailUnavailableReason.KEY_UNDECLARED
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "mail.json").write_text(result.model_dump_json(), encoding="utf-8")
    text = "".join(p.read_text(encoding="utf-8") for p in run_dir.rglob("*") if p.is_file())
    assert PASSWORD not in text and USER not in text and "other-canary-value" not in text
