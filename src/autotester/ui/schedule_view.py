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

from autotester.schema.project import Project
from autotester.schema.schedule import ScheduleConfig, ScheduleMode, ScheduleZone
from autotester.stages.schedule_gate import credential_state
from autotester.stages.schedule_store import project_records_path, read_heartbeat, read_records
from autotester.stages.schedule_time import slot_instants
from autotester.stages.schedule_wiring import schedule_paths
from autotester.stages.scheduler import scheduler_health
from autotester.store.project_store import ProjectStore
from autotester.ui import theme

_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_LOOKAHEAD = timedelta(days=8)


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


def _form(slug: str, cfg: ScheduleConfig) -> str:
    modes = _options([m.value for m in ScheduleMode], cfg.mode.value)
    zones = _options([z.value for z in ScheduleZone], cfg.timezone.value)
    on = set(cfg.weekly.weekdays) if cfg.weekly else set()
    days = " ".join(f"<label><input type='checkbox' name='weekdays' value='{i}'"
                    f"{' checked' if i in on else ''}> {d}</label>" for i, d in enumerate(_DAYS))
    one_offs = "\n".join(s.strftime("%Y-%m-%dT%H:%M") for s in cfg.one_offs)
    weekly_at = cfg.weekly.at if cfg.weekly else ""
    return (
        f"<form method='post' action='/projects/{escape(slug)}/schedule'>"
        f"<div class='field'><label for='mode'>Mode</label><select id='mode' name='mode'>"
        f"{modes}</select></div>"
        f"<div class='field'><label for='timezone'>Time zone (no daylight saving)</label>"
        f"<select id='timezone' name='timezone'>{zones}</select></div>"
        f"<div class='field'><label for='fixed_at'>Daily time (fixed), HH:MM</label>"
        f"<input id='fixed_at' name='fixed_at' value='{escape(cfg.fixed_at or '')}'></div>"
        f"<div class='field'><label>Weekly days (custom)</label>{days}</div>"
        f"<div class='field'><label for='weekly_at'>Weekly time (custom), HH:MM</label>"
        f"<input id='weekly_at' name='weekly_at' value='{escape(weekly_at)}'></div>"
        f"<div class='field'><label for='one_offs'>One-off times (custom), one per line, "
        f"YYYY-MM-DDTHH:MM</label><textarea id='one_offs' name='one_offs'>{escape(one_offs)}"
        "</textarea></div><button class='btn btn-primary' type='submit'>Save schedule</button>"
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


def _history(slug: str) -> str:
    records = read_records(project_records_path(schedule_paths().records, slug))[-5:]
    if not records:
        return "<p class='subtitle'>No scheduled slot has been decided yet.</p>"
    rows = "".join(
        f"<tr><td>{r.instant:%Y-%m-%d %H:%M} UTC</td><td>{escape(r.outcome.value)}</td>"
        f"<td>{escape(r.detail or '')}</td></tr>" for r in reversed(records))
    return f"<table><tr><th>Slot</th><th>Outcome</th><th>Why</th></tr>{rows}</table>"


def _status(cfg: ScheduleConfig, project: Project, store: ProjectStore, now: datetime) -> str:
    if cfg.mode is ScheduleMode.MANUAL:
        return ""
    nxt = slot_instants(cfg, now, now + _LOOKAHEAD)
    when = f"{nxt[0]:%Y-%m-%d %H:%M} UTC" if nxt else (
        "paused" if cfg.paused else "none in the next 8 days")
    health = scheduler_health(cfg, read_heartbeat(schedule_paths().heartbeat), now).state.value
    creds = credential_state(project, store).value
    return (f"<p>Next run: <b>{escape(when)}</b> &middot; owner: {escape(cfg.owner or '-')}"
            f" &middot; scheduler: "
            f"{theme.pill(escape(health), 'positive' if health == 'healthy' else 'warning')}"
            f" &middot; credentials: "
            f"{theme.pill(escape(creds), 'positive' if creds == 'provisioned' else 'warning')}</p>")


def schedule_card(slug: str, project: Project, store: ProjectStore, *, manage: bool,
                  now: datetime | None = None) -> str:
    """The card for one project; `manage` shows the edit controls."""
    now = now or datetime.now(UTC)
    cfg = project.schedule or ScheduleConfig()
    scheduled = cfg.mode is not ScheduleMode.MANUAL
    state = f" ({'paused' if cfg.paused else 'active'})" if scheduled else ""
    head = (f"<p>{theme.pill(escape(cfg.mode.value), 'neutral')} "
            f"{escape(_describe(cfg))}{state}</p>")
    body = head + _status(cfg, project, store, now) + _history(slug)
    if manage:
        body += _buttons(slug, cfg) + _form(slug, cfg)
    return theme.card(body, title="Scheduled test")
