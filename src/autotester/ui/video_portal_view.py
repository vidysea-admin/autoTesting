"""The HTML of the video portal: player page, request-access page, shared list, requests list.

One job: build the markup (T-198b / G9). Every value that came from a person (a comment, a
label, an email) goes through `esc` here, so a comment such as `<script>alert(1)</script>`
is text on every page. Controls the viewer may not use are not rendered (TP2/TP4: the UI hides,
the server refuses). Forms have visible labels and use native, keyboard-operable controls.
"""

from __future__ import annotations

from html import escape

from autotester.schema.project import Source
from autotester.schema.team_enums import AccessRequestStatus
from autotester.schema.video_share import AccessRequest, VideoComment
from autotester.ui import theme

SEEK_SCRIPT = (
    "<script>(function(){var p=document.getElementById('player');if(!p){return;}"
    "document.addEventListener('click',function(e){var b=e.target.closest('[data-seek]');"
    "if(b){p.currentTime=parseFloat(b.getAttribute('data-seek'));p.play();}"
    "var n=e.target.closest('[data-now]');"
    "if(n){document.getElementById('at_s').value=Math.floor(p.currentTime);}});})();</script>"
)


def esc(value: object) -> str:
    return escape(str(value), quote=True)


def time_label(seconds: float) -> str:
    whole = int(seconds)
    h, rest = divmod(whole, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _form(action: str, inner: str, label: str, css: str = "btn btn-sm") -> str:
    return (f"<form method='post' action='{esc(action)}' style='display:inline'>{inner}"
            f"<button class='{css}' type='submit'>{esc(label)}</button></form>")


def request_access_page(post_path: str, existing: AccessRequest | None = None) -> str:
    """What a signed-in person without access sees: no title, no player, only how to ask. The
    same page answers an unknown video, so it cannot be used to find out what exists (TP1/TP3)."""
    status = ""
    if existing is not None and existing.status is AccessRequestStatus.PENDING:
        status = "<p><strong>Your request is waiting for a decision.</strong></p>"
    elif existing is not None and existing.status is AccessRequestStatus.DECLINED:
        status = "<p>Your last request was declined. You can ask again.</p>"
    body = (
        "<h1>You do not have access to this video</h1>" + status
        + "<p>Ask for access. Your request goes to the person who uploaded the video, a "
        "sub-admin of its project, or an admin. You will see the answer here and under "
        "<a href='/shared'>Videos</a>.</p>"
        + _form(post_path, "", "Request access", "btn btn-primary"))
    return theme.page("Request access", theme.card(body))


def request_sent_page() -> str:
    body = ("<h1>Request sent</h1><p>If the video exists, the people who can approve it have "
            "been asked. Check <a href='/shared'>Videos</a> for the answer.</p>")
    return theme.page("Request sent", theme.card(body))


def _comment_li(c: VideoComment, base: str, *, can_edit: bool, can_delete: bool,
                can_promote: bool) -> str:
    edited = " <em>(edited)</em>" if c.edited_at else ""
    promoted = " <em>(pointer)</em>" if c.pointer_line else ""
    acts = ""
    if can_edit:
        acts += (f"<details style='display:inline'><summary>Edit</summary>"
                 f"<form method='post' action='{base}/comments/{c.id}/edit'>"
                 f"<label for='edit-{c.id}'>Comment text</label>"
                 f"<textarea id='edit-{c.id}' name='text' required maxlength='2000'>"
                 f"{esc(c.text)}</textarea><button class='btn btn-sm' type='submit'>Save"
                 "</button></form></details> ")
    if can_delete:
        acts += _form(f"{base}/comments/{c.id}/delete", "", "Delete")
    if can_promote and not c.pointer_line:
        acts += _form(f"{base}/comments/{c.id}/promote", "", "Make a pointer")
    return (f"<li id='comment-{c.id}'><button type='button' class='btn btn-sm' "
            f"data-seek='{c.at_s:g}'>{time_label(c.at_s)}</button> "
            f"<strong>{esc(c.author)}</strong>: "
            f"<span class='comment-text'>{esc(c.text)}</span>{edited}{promoted} {acts}</li>")


def _comment_form(base: str) -> str:
    return (
        f"<form method='post' action='{base}/comments'>"
        "<div class='field'><label for='at_s'>Time in seconds</label>"
        "<input id='at_s' name='at_s' type='text' inputmode='decimal' value='0' required> "
        "<button class='btn btn-sm' type='button' data-now='1'>Use current time</button></div>"
        "<div class='field'><label for='text'>Comment</label>"
        "<textarea id='text' name='text' required maxlength='2000'></textarea></div>"
        "<button class='btn btn-primary' type='submit'>Add comment</button></form>")


def _share_panel(base: str, link_since: str | None, people: list[str]) -> str:
    live = (f"<p>A share link is live (made {esc(link_since)}). Opening it needs sign-in and "
            "gives nothing by itself.</p>" if link_since else "<p>No share link yet.</p>")
    who = "".join(f"<li>{esc(e)}</li>" for e in people) or "<li>nobody yet</li>"
    add = (f"<form method='post' action='{base}/shares'>"
           "<div class='field'><label for='share-email'>Account email</label>"
           "<input id='share-email' name='email' type='email' required></div>"
           "<div class='field'><label for='share-change'>Change</label>"
           "<select id='share-change' name='change'><option value='add'>share with</option>"
           "<option value='remove'>stop sharing with</option></select></div>"
           "<button class='btn btn-sm' type='submit'>Save</button></form>")
    return (live + _form(f"{base}/share-link", "", "Create a new share link")
            + (_form(f"{base}/share-link/revoke", "", "Revoke the link") if link_since else "")
            + f"<h3>Shared with</h3><ul>{who}</ul>" + add)


def player_page(slug: str, source: Source, comments: list[VideoComment], *, viewer: str,
                moderator: bool, can_comment: bool, can_promote: bool,
                share: tuple[str | None, list[str]] | None) -> str:
    base = f"/projects/{esc(slug)}/videos/{esc(source.id)}"
    items = "".join(_comment_li(
        c, base, can_edit=can_comment and c.author == viewer,
        can_delete=can_comment and (c.author == viewer or moderator),
        can_promote=can_promote) for c in comments) or "<li>No comments yet.</li>"
    player = (f"<video id='player' controls preload='metadata' style='max-width:100%' "
              f"src='{base}/media'></video>")
    body = (theme.breadcrumb(("Videos", "/shared"), (esc(source.label or source.id), None))
            + f"<h1>{esc(source.label or 'Video')}</h1>" + theme.card(player)
            + theme.card(f"<ul class='comments'>{items}</ul>"
                         + (_comment_form(base) if can_comment else ""), title="Comments"))
    if share is not None:
        body += theme.card(_share_panel(base, share[0], share[1]), title="Share")
    return theme.page(esc(source.label or "Video"), body + SEEK_SCRIPT)


def share_link_page(link: str, back: str) -> str:
    body = ("<h1>Share link created</h1><p>Copy it now; it is not shown again. Anyone who "
            "opens it must sign in, and only people with access see the video.</p>"
            f"<p><input aria-label='Share link' readonly size='70' value='{esc(link)}'></p>"
            f"<a class='btn' href='{esc(back)}'>Back to the video</a>")
    return theme.page("Share link", theme.card(body))


def shared_page(videos: list[tuple[str, Source]], mine: list[AccessRequest],
                labels: dict[tuple[str, str], str]) -> str:
    rows = "".join(
        f"<li><a href='/projects/{esc(slug)}/videos/{esc(s.id)}'>{esc(s.label or s.id)}</a> "
        f"<small>({esc(slug)})</small></li>" for slug, s in videos) or "<li>Nothing yet.</li>"
    asked = "".join(
        f"<li>{esc(labels.get((r.slug, r.video_id), 'A video'))}: {esc(r.status.value)}</li>"
        for r in mine) or "<li>No requests.</li>"
    body = ("<h1>Videos</h1>" + theme.card(f"<ul>{rows}</ul>", title="Shared with me")
            + theme.card(f"<ul>{asked}</ul>", title="My access requests"))
    return theme.page("Videos", body)


def approver_requests_page(pending: list[AccessRequest], labels: dict[tuple[str, str], str]) -> str:
    rows = "".join(
        f"<li>{esc(r.requester)} asked for {esc(labels.get((r.slug, r.video_id), 'a video'))} "
        + _form(f"/access-requests/{r.id}/approve", "", "Approve", "btn btn-sm btn-primary")
        + _form(f"/access-requests/{r.id}/decline", "", "Decline") + "</li>"
        for r in pending) or "<li>No requests waiting.</li>"
    return theme.page("Access requests", "<h1>Access requests</h1>"
                      + theme.card(f"<ul>{rows}</ul>", title="Waiting for you"))
