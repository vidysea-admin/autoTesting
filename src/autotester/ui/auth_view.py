"""Markup for the sign-in, sign-up and "waiting for an admin" pages (T-204).

A minimal layout (stylesheet, brand, no project sidebar), because these pages are seen
before anyone is known. Every form control has a visible label (AU26).
"""

from __future__ import annotations

from html import escape

from autotester.auth.passwords import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH
from autotester.ui import theme
from autotester.ui.theme_style import PAGE_STYLE

_BRAND = ("<header class='topbar'><a class='brand' href='/'><span class='brand-mark'>AT</span>"
          "<span class='brand-name'>AutoTester</span></a></header>")

# AU16: /favicon.ico is not in the closed public set, so a signed-out page must not request it.
_ICON = "<link rel='icon' href='data:,'>"


def auth_page(title: str, body: str) -> str:
    """`title` and `body` must already be escaped by the caller."""
    return (f"<!doctype html><title>{title} — AutoTester</title>{_ICON}{PAGE_STYLE}{_BRAND}"
            f"<div class='layout'><main style='max-width:440px;margin:40px auto'>"
            f"{body}</main></div>")


# Show/hide toggle for a password field. Same inline-onclick pattern as the settings page
# (routes_settings.py provider_settings_view `_EYE`); no CSP is sent, and nothing external loads
# (AU16). type='button' so it never submits; aria-label always names what the next click does.
_EYE = ("<button type='button' class='btn btn-sm' aria-label='Show password' "
        "onclick=\"var i=this.parentNode.querySelector('input');"
        "i.type=i.type==='password'?'text':'password';"
        "var h=i.type==='text';this.textContent=h?'Hide':'Show';"
        "this.setAttribute('aria-label',h?'Hide password':'Show password');\">Show</button>")


def _field(label: str, name: str, kind: str, extra: str = "") -> str:
    style = " style='flex:1'" if kind == "password" else ""
    input_ = f"<input id='{name}' name='{name}' type='{kind}'{style} required {extra}>"
    if kind == "password":
        input_ = f"<div style='display:flex;gap:6px'>{input_}{_EYE}</div>"
    return f"<div class='field'><label for='{name}'>{label}</label>{input_}</div>"


def login_page(next_path: str, message: str = "") -> str:
    note = f"<p class='subtitle' role='alert'>{escape(message)}</p>" if message else ""
    form = (
        "<form method='post' action='/auth/login'>"
        f"<input type='hidden' name='next' value='{escape(next_path)}'>"
        + _field("Email", "email", "email", "autocomplete='username'")
        + _field("Password", "password", "password", "autocomplete='current-password'")
        + "<button class='btn btn-primary' type='submit'>Sign in</button></form>"
        "<p style='margin-top:14px'>No account yet? <a href='/auth/signup'>Sign up</a></p>"
    )
    return auth_page("Sign in", "<h1>Sign in</h1>" + note + theme.card(form))


def signup_page(message: str = "") -> str:
    note = f"<p class='subtitle' role='alert'>{escape(message)}</p>" if message else ""
    form = (
        "<form method='post' action='/auth/signup'>"
        + _field("Email", "email", "email", "autocomplete='username'")
        + _field(f"Password ({MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters)",
                 "password", "password",
                 f"minlength='{MIN_PASSWORD_LENGTH}' maxlength='{MAX_PASSWORD_LENGTH}' "
                 "autocomplete='new-password'")
        + "<button class='btn btn-primary' type='submit'>Create account</button></form>"
        "<p style='margin-top:14px'>Already have an account? <a href='/auth/login'>Sign in</a></p>"
    )
    body = ("<h1>Create an account</h1><p class='subtitle'>A new account has no access "
            "until an administrator adds it to a group.</p>" + note + theme.card(form))
    return auth_page("Sign up", body)


def logout_form() -> str:
    return ("<form method='post' action='/auth/logout' style='display:inline'>"
            "<button class='btn btn-sm' type='submit'>Sign out</button></form>")


def waiting_page(email: str) -> str:
    """AU6: what an account with no group sees. Names the role to ask; lists no users."""
    body = theme.card(
        f"<p>You are signed in as <strong>{escape(email)}</strong>, but your account has "
        "no access yet.</p><p>Ask an <strong>administrator</strong> to add you to a group. "
        "Your access starts on your next click after they do.</p>"
        f"<p style='margin-top:14px'>{logout_form()}</p>",
        title="Waiting for an administrator",
    )
    return auth_page("Waiting for access", body)
