"""A browser's persistent state: the wiped entry profile (RU5) and a role account's saved login.

Two halves, one subject. `wipe_entry_profile` establishes a logged-out entry profile before any
browser opens. The session half (mongo-store U12, M38-M40; D-123: plain, no encryption, no key)
keeps a Playwright `storage_state` per `<slug>|<account_id>` in `browser_sessions`, only with the
credentials area on mongo: scoped to the project's `allowed_domains` on the way in and out,
discarded when expired or foreign, never restored into an entry run, and registered with the
redactor so no cookie or token value reaches a log, trace, prompt or report. With the store off
every function here is a no-op and nothing is read or written.
"""

import contextlib
import json
import shutil
import time
from pathlib import Path
from typing import Any

from autotester.browser.secrets import _host_matches, host_of
from autotester.schema.project import Project

SESSION_COLLECTION = "browser_sessions"
MAX_AGE_S = 24 * 3600  # a saved login is never replayed older than this, whatever its cookies say
SKEW_S = 300  # a save time further ahead than this is a clock lie or tampering, not a login
MIN_VALUE_LEN = 8  # shorter values ("1", "en") would corrupt every trace if masked everywhere
MAX_MASKED = 200
ENTRY_SUFFIX = "-entry-test"
MAIN_ACCOUNT = "_project"  # the project-level login; not a valid RoleAccount id, so no collision


def wipe_entry_profile(profile: Path) -> None:
    """Remove the entry profile and positively establish it is gone (RU5, C12).
    An already-absent directory is success. A failed removal, a directory still
    present, or an existence check that itself raises all propagate as `OSError`
    (never `ignore_errors`, never `os.path.lexists`, which reads an error as
    'absent'), so the caller never starts a browser on a logged-in profile."""
    try:
        with contextlib.suppress(FileNotFoundError):
            shutil.rmtree(profile)
        present = profile.exists()
    except OSError as exc:
        cause = f"{type(exc).__name__}: {exc}"
        raise OSError(f"entry profile not removed: {profile} ({cause})") from exc
    if present:
        raise OSError(f"entry profile not removed: {profile} (still present after removal)")


# ---- the session store (M38-M40) --------------------------------------------------------------


class SessionRefused(ValueError):
    """An id, a document or a write the session store will not accept. Never quotes a value."""


def session_id(slug: str, account_id: str) -> str:
    if not slug or not account_id or "|" in slug or "|" in account_id:
        raise SessionRefused("a session id needs a project slug and an account id, no '|'")
    return f"{slug}|{account_id}"


def _collection() -> Any:
    """`browser_sessions` when the credentials area is on mongo, else `None`."""
    from autotester.store.mongo_routes import store_selection  # lazy: it imports core.env

    if store_selection()["credentials"] != "mongo":
        return None
    from autotester.store.mongo_backend import default_store

    return default_store().collection(SESSION_COLLECTION)


def _put_session(coll: Any, doc: dict[str, Any]) -> None:
    """The ONLY write of a session document (M38): by `_id`, replacing in place."""
    coll.replace_one({"_id": doc["_id"]}, doc, upsert=True)
    from autotester.store.mongo_backend import default_backend

    default_backend().rearm()  # the write gate takes the new values (M34), on one client


def _in_scope(project: Project, host: str) -> bool:
    return any(_host_matches(host, d) for d in project.allowed_domains)


def _dicts(value: Any) -> list[dict[str, Any]]:
    """The dict members of a list; anything else (a number, a string, a bad member) is nothing."""
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def scope_state(state: dict[str, Any], project: Project) -> dict[str, Any]:
    """`state` with every cookie and origin outside the project's `allowed_domains` dropped (M38).
    Fails closed: a malformed entry or an unparseable host is dropped, never kept; an origin keeps
    only well-formed `localStorage` items, so nothing downstream meets a bad one."""
    cookies = [c for c in _dicts(state.get("cookies"))
               if _in_scope(project, str(c.get("domain") or "").lstrip("."))]
    origins = [{"origin": str(o["origin"]),
                "localStorage": [i for i in _dicts(o.get("localStorage"))
                                 if isinstance(i.get("name"), str) and "value" in i]}
               for o in _dicts(state.get("origins"))
               if _in_scope(project, host_of(str(o.get("origin") or "")))]
    return {"cookies": cookies, "origins": origins}


def _expired(cookie: dict[str, Any], now: float) -> bool:
    expires = cookie.get("expires")
    return isinstance(expires, (int, float)) and 0 < expires <= now


def _hosts(state: dict[str, Any]) -> list[str]:
    found = {str(c.get("domain") or "").lstrip(".") for c in state["cookies"]}
    found |= {host_of(str(o.get("origin") or "")) for o in state["origins"]}
    return sorted(h for h in found if h)


def save_session(project: Project, account_id: str, state: dict[str, Any], *,
                 now: float | None = None) -> dict[str, Any] | None:
    """Store `state` (scoped, unexpired cookies only) for one account and return what was stored,
    or `None` with the store off or nothing in scope (then any held document goes: a login that
    holds nothing is no login). Never touches another project's document."""
    coll = _collection()
    if coll is None:
        return None
    sid, at = session_id(project.slug, account_id), time.time() if now is None else now
    held = coll.find_one({"_id": sid})
    if held is not None and held.get("p") != project.slug:
        raise SessionRefused("a session document of another project holds this id")
    kept = scope_state(state, project)
    kept["cookies"] = [c for c in kept["cookies"] if not _expired(c, at)]
    if not kept["cookies"] and not kept["origins"]:
        coll.delete_one({"_id": sid, "p": project.slug})
        return None
    live = [c["expires"] for c in kept["cookies"] if isinstance(c.get("expires"), (int, float))
            and c["expires"] > 0]
    _put_session(coll, {"_id": sid, "p": project.slug, "state": kept, "saved_at": at,
                        "expires_at": min([at + MAX_AGE_S, *live]), "hosts": _hosts(kept)})
    return kept


def _readable(doc: dict[str, Any], at: float) -> dict[str, Any] | None:
    """The `state` of a stored document that is well formed and still within `MAX_AGE_S` of when it
    was saved, else `None`. The age cap is re-applied here, not trusted from `expires_at`, so a
    tampered far-future expiry (or save time) buys nothing."""
    expires, saved, state = doc.get("expires_at"), doc.get("saved_at"), doc.get("state")
    if not all(isinstance(n, (int, float)) and not isinstance(n, bool) for n in (expires, saved)):
        return None
    if not isinstance(state, dict) or saved > at + SKEW_S:
        return None
    if min(expires, saved + MAX_AGE_S) <= at:
        return None
    parts = (state.get("cookies", []), state.get("origins", []))
    return state if all(isinstance(part, list) for part in parts) else None


def load_session(project: Project, account_id: str, *, now: float | None = None
                 ) -> dict[str, Any] | None:
    """The stored state of one account, re-scoped to the project's CURRENT domains, or `None`.
    An expired or unreadable document is deleted; another project's is ignored and left alone."""
    coll = _collection()
    if coll is None:
        return None
    sid, at = session_id(project.slug, account_id), time.time() if now is None else now
    doc = coll.find_one({"_id": sid})
    if doc is None or doc.get("p") != project.slug or doc.get("_id") != sid:
        return None
    if (state := _readable(doc, at)) is None:
        coll.delete_one({"_id": sid, "p": project.slug})
        return None
    kept = scope_state(state, project)
    kept["cookies"] = [c for c in kept["cookies"] if not _expired(c, at)]
    return kept if kept["cookies"] or kept["origins"] else None


def forget_session(project: Project, account_id: str) -> bool:
    """An explicit logout or delete: the document goes, so nothing restores it (M39)."""
    coll = _collection()
    return False if coll is None else bool(
        coll.delete_one({"_id": session_id(project.slug, account_id), "p": project.slug}))


# ---- redaction (M40) ----------------------------------------------------------------------------


def _leaves(value: Any, depth: int = 0) -> list[str]:
    if isinstance(value, str):
        return [value]
    if depth > 4 or not isinstance(value, (dict, list)):
        return []
    items = value.values() if isinstance(value, dict) else value
    return [leaf for item in items for leaf in _leaves(item, depth + 1)]


def session_values(state: dict[str, Any], label: str = "session") -> dict[str, str]:
    """Every cookie and `localStorage` value of `state` worth masking, longest first, capped.
    A value that parses as JSON also contributes its string leaves (a token inside a blob)."""
    raw = [str(c.get("value") or "") for c in _dicts(state.get("cookies"))]
    for origin in _dicts(state.get("origins")):
        raw += [str(i.get("value") or "") for i in _dicts(origin.get("localStorage"))]
    found: dict[str, None] = {}
    for text in raw:
        found[text] = None
        if text[:1] in "{[":
            with contextlib.suppress(ValueError):
                found.update(dict.fromkeys(_leaves(json.loads(text))))
    values = sorted((v for v in found if len(v) >= MIN_VALUE_LEN), key=len, reverse=True)
    return {f"{label}:{i}": v for i, v in enumerate(values[:MAX_MASKED])}


def stored_session_values() -> dict[str, str]:
    """`session_values` of every stored session of every project; `{}` with the store off."""
    coll = _collection()
    found: dict[str, str] = {}
    for doc in [] if coll is None else coll.find({}):
        state = doc.get("state")
        if isinstance(state, dict):
            found.update(session_values(state, f"session@{doc.get('_id')}"))
    return found


# ---- the live browser ---------------------------------------------------------------------------


def _origin_script(origins: list[dict[str, Any]]) -> str:
    """An init script that fills `localStorage` per origin where a key is absent (never clobbers
    a token the app refreshed). The origin check lives in the script itself."""
    items = {str(o["origin"]): {str(i["name"]): str(i["value"]) for i in o["localStorage"]
                                if "name" in i and "value" in i}
             for o in origins if o.get("origin") and o.get("localStorage")}
    if not items:
        return ""
    return ("(() => { try { const m = " + json.dumps(items) + "; const s = m[location.origin]; "
            "if (!s) return; for (const [k, v] of Object.entries(s)) "
            "{ if (localStorage.getItem(k) === null) localStorage.setItem(k, v); } } "
            "catch (e) {} })();")


def capture_session(session: Any, project: Project, account_id: str) -> bool:
    """After a login: export the context's `storage_state` IN MEMORY (never to a path) and store
    it scoped (M38). The cookie values join the run's redactor. False: store off or nothing kept."""
    context = getattr(session, "_context", None)
    if context is None or _collection() is None:
        return False
    kept = save_session(project, account_id, context.storage_state())
    if kept is None:
        return False
    session.secrets.mask_also(session_values(kept, f"session:{account_id}"))
    return True


def restore_session(session: Any, project: Project, account_id: str) -> bool:
    """Before a run: put the account's stored, unexpired, scoped state into its own context (M39).
    Never into an entry run (RU5): such a session starts logged out. False: nothing restored."""
    context = getattr(session, "_context", None)
    paths = getattr(session, "paths", None)
    if context is None or str(getattr(paths, "slug", "")).endswith(ENTRY_SUFFIX):
        return False
    state = load_session(project, account_id)
    if state is None:
        return False
    session.secrets.mask_also(session_values(state, f"session:{account_id}"))
    if state["cookies"]:
        context.add_cookies(state["cookies"])
    if script := _origin_script(state["origins"]):
        context.add_init_script(script)
    return True
