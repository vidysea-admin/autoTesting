"""The project schedule card (TS1): what the schedule is, when it fires next, what it did last.

One job: render HTML for `routes_schedule.py` and the project page. It reads the schedule, the
scheduler heartbeat and the per-project slot records (all through the existing stores) and the
read-only TS5 credential state; it writes nothing. The edit controls render only when `manage`
is true (the viewer holds `schedule.manage` here); the server enforces the key regardless
(`auth/policy.py`), so hiding the forms is a courtesy, not the gate.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from html import escape

from autotester.core.localtime import zone
from autotester.schema.project import Project
from autotester.schema.schedule import (
    ScheduleConfig,
    ScheduleMode,
    SchedulerHealth,
    ScheduleZone,
    SlotRecord,
)
from autotester.stages.schedule_gate import credential_state
from autotester.stages.schedule_store import project_records_path, read_heartbeat, read_records
from autotester.stages.schedule_time import slot_instants
from autotester.stages.schedule_wiring import schedule_paths
from autotester.stages.scheduler import scheduler_health
from autotester.store.project_store import ProjectStore
from autotester.ui import theme

_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_LOOKAHEAD = timedelta(days=8)
_PREVIEW_SPAN = timedelta(days=60)


def _describe(cfg: ScheduleConfig) -> str:
    zone = cfg.timezone.value
    if cfg.mode is ScheduleMode.FIXED:
        return f"every day at {cfg.fixed_at} {zone}"
    if cfg.mode is ScheduleMode.CUSTOM:
        parts = [f"once at {s:%Y-%m-%d %H:%M} {zone}" for s in cfg.one_offs]
        if cfg.weekly is not None:
            days = ", ".join(_DAYS[d] for d in cfg.weekly.weekdays)
            parts.append(f"every {days} at {cfg.weekly.at} {zone}")
        return "; ".join(parts)
    return "manual (the Run button only; nothing is scheduled)"


def _options(choices: list[str], chosen: str) -> str:
    return "".join(f"<option value='{c}'{' selected' if c == chosen else ''}>{c}</option>"
                   for c in choices)


def _values(cfg: ScheduleConfig, draft: dict[str, object] | None) -> dict[str, object]:
    """The field values to show: what the user typed (refused or previewed save), else saved."""
    if draft is not None:
        return draft
    return {"mode": cfg.mode.value, "timezone": cfg.timezone.value,
            "fixed_at": cfg.fixed_at or "",
            "weekdays": [str(d) for d in (cfg.weekly.weekdays if cfg.weekly else [])],
            "weekly_at": cfg.weekly.at if cfg.weekly else "",
            "one_offs": "\n".join(s.strftime("%Y-%m-%dT%H:%M") for s in cfg.one_offs)}


def _form(slug: str, cfg: ScheduleConfig, draft: dict[str, object] | None = None) -> str:
    v = _values(cfg, draft)
    modes = _options([m.value for m in ScheduleMode], str(v["mode"]))
    zones = _options([z.value for z in ScheduleZone], str(v["timezone"]))
    fixed_at, weekly_at, one_offs = (escape(str(v[k])) for k in
                                     ('fixed_at', 'weekly_at', 'one_offs'))
    on = {str(d) for d in v["weekdays"]}  # type: ignore[attr-defined]
    days = " ".join(f"<label><input type='checkbox' name='weekdays' value='{i}'"
                    f"{' checked' if str(i) in on else ''}> {d}</label>"
                    for i, d in enumerate(_DAYS))
    return (
        f"<form method='post' action='/projects/{escape(slug)}/schedule'>"
        f"<div class='field'><label for='mode'>Mode</label><select id='mode' name='mode'>"
        f"{modes}</select></div>"
        f"<div class='field'><label for='timezone'>Time zone (no daylight saving)</label>"
        f"<select id='timezone' name='timezone'>{zones}</select></div>"
        f"<div class='field'><label for='fixed_at'>Daily time (fixed), HH:MM</label>"
        f"<input id='fixed_at' name='fixed_at' value='{fixed_at}'></div>"
        f"<div class='field'><label>Weekly days (custom)</label>{days}</div>"
        f"<div class='field'><label for='weekly_at'>Weekly time (custom), HH:MM</label>"
        f"<input id='weekly_at' name='weekly_at' value='{weekly_at}'></div>"
        f"<div class='field'><label for='one_offs'>One-off times (custom), one per line, "
        f"YYYY-MM-DDTHH:MM</label><textarea id='one_offs' name='one_offs'>{one_offs}"
        "</textarea></div><button class='btn' type='submit' name='intent' value='preview'>"
        "Preview next three runs</button> "
        "<button class='btn btn-primary' type='submit'>Save schedule</button>"
        "</form>"
    )


def _buttons(slug: str, cfg: ScheduleConfig) -> str:
    def one(action: str, label: str) -> str:
        return (f"<form method='post' action='/projects/{escape(slug)}/schedule/{action}' "
                f"style='display:inline'><button class='btn' type='submit'>{label}</button></form>")

    if cfg.mode is ScheduleMode.MANUAL:
        return ""
    return (one("resume", "Resume") if cfg.paused else one("pause", "Pause")) \
        + one("delete", "Delete schedule")


def _why(rec: SlotRecord) -> str:
    """The reason column: the detail, and for a skipped slot the blocking entry's id (TS4)."""
    parts = [rec.detail or ""]
    if rec.blocking_entry_id:
        parts.insert(0, f"project busy: blocked by run {rec.blocking_entry_id}; "
                        "this slot was skipped, not retried")
    return " - ".join(p for p in parts if p)


def _history(slug: str) -> str:
    records = read_records(project_records_path(schedule_paths().records, slug))[-5:]
    if not records:
        return "<p class='subtitle'>No scheduled slot has been decided yet.</p>"
    rows = "".join(
        f"<tr><td>{r.instant:%Y-%m-%d %H:%M} UTC</td><td>{escape(r.outcome.value)}</td>"
        f"<td>{escape(_why(r))}</td></tr>" for r in reversed(records))
    return f"<table><tr><th>Slot</th><th>Outcome</th><th>Why</th></tr>{rows}</table>"


def next_fires(cfg: ScheduleConfig, now: datetime, count: int = 3) -> list[datetime]:
    """The next fire instants (UTC) from the one schedule computation, `slot_instants`."""
    return slot_instants(cfg, now, now + _PREVIEW_SPAN)[:count]


def preview_html(cfg: ScheduleConfig, now: datetime, heading: str = "Next three runs") -> str:
    """The next three fire times in the schedule's own zone (and UTC), shown before saving."""
    fires = next_fires(cfg, now)
    if not fires:
        return f"<p role='status'>{heading}: none in the next 60 days.</p>"
    tz, name = zone(cfg.timezone), cfg.timezone.value
    items = "".join(f"<li>{f.astimezone(tz):%a %Y-%m-%d %H:%M} {name} ({f:%H:%M} UTC)</li>"
                    for f in fires)
    return f"<div role='status'><p>{heading}:</p><ol>{items}</ol></div>"


def _status(slug: str, cfg: ScheduleConfig, project: Project, store: ProjectStore,
            now: datetime) -> str:
    if cfg.mode is ScheduleMode.MANUAL:
        return ""
    nxt = slot_instants(cfg, now, now + _LOOKAHEAD)
    when = f"{nxt[0]:%Y-%m-%d %H:%M} UTC" if nxt else (
        "paused" if cfg.paused else "none in the next 8 days")
    status = scheduler_health(cfg, read_heartbeat(schedule_paths().heartbeat), now)
    health = status.state.value
    health_text = (f"scheduler stale since {status.since:%Y-%m-%d %H:%M} UTC"
                   if status.state is SchedulerHealth.STALE and status.since else health)
    creds = credential_state(project, store).value
    cred_pill = theme.pill(escape(creds), "positive" if creds == "provisioned" else "warning")
    if creds != "provisioned":
        cred_pill += (f" <a href='/projects/{escape(slug)}/env'>Declare or set credentials on the"
                      " Credentials page</a>")
    return (f"<p>Next run: <b>{escape(when)}</b> &middot; owner: {escape(cfg.owner or '-')}"
            f" &middot; scheduler: "
            f"{theme.pill(escape(health_text), 'positive' if health == 'healthy' else 'warning')}"
            f" &middot; credentials: {cred_pill}</p>") + preview_html(cfg, now)


def schedule_card(slug: str, project: Project, store: ProjectStore, *, manage: bool,
                  now: datetime | None = None, error: str | None = None,
                  draft: dict[str, object] | None = None,
                  preview: ScheduleConfig | None = None) -> str:
    """The card for one project; `manage` shows the edit controls. `error` is an inline refusal
    and `draft` the typed values it keeps; `preview` is an unsaved config whose next three runs
    are shown above the form."""
    now = now or datetime.now(UTC)
    cfg = project.schedule or ScheduleConfig()
    scheduled = cfg.mode is not ScheduleMode.MANUAL
    state = f" ({'paused' if cfg.paused else 'active'})" if scheduled else ""
    head = (f"<p>{theme.pill(escape(cfg.mode.value), 'neutral')} "
            f"{escape(_describe(cfg))}{state}</p>")
    body = head + _status(slug, cfg, project, store, now) + _history(slug)
    if manage:
        note = f"<p class='subtitle' role='alert'>{escape(error)}</p>" if error else ""
        shown = (preview_html(preview, now, "Preview, not saved yet. Next three runs")
                 if preview is not None else "")
        body += _buttons(slug, cfg) + note + shown + _form(slug, cfg, draft)
    return theme.card(body, title="Scheduled test")
