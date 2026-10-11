"""The Group 10 (team features) vocabulary file: every closed value set the team units add.

One job: be the single home of the Group 10 closed vocabularies (schedule mode and zone, slot
outcome, scheduler health, how a run was requested, where a source came from).
`schema/enums.py` stays the home of every pre-existing vocabulary and is at its 300-line cap,
so nothing new goes there. A value defined
in both files, or re-typed as a bare literal in a stage, is a defect (one concept, one place);
`tests/test_team_enums_home.py` checks both. Later units (delivery status)
append their vocabulary here.
"""

from __future__ import annotations

from enum import StrEnum


class ScheduleMode(StrEnum):
    MANUAL = "manual"
    FIXED = "fixed"
    CUSTOM = "custom"


class ScheduleZone(StrEnum):
    """The only two zones a schedule may use (Umesh, 2026-10-07). IST is +05:30, no DST."""

    UTC = "UTC"
    IST = "IST"


class SlotOutcome(StrEnum):
    """What a tick decided for one slot. A record carries exactly one of these."""

    ENQUEUED = "enqueued"
    CATCH_UP = "catch_up"
    MISSED = "missed"
    SKIPPED_OVERLAP = "skipped_overlap"
    BLOCKED_NO_CREDENTIALS = "blocked_no_credentials"
    REFUSED = "refused"
    FAILED = "failed"


class SchedulerHealth(StrEnum):
    NOT_APPLICABLE = "not_applicable"  # a manual schedule never ticks
    NEVER_TICKED = "never_ticked"
    HEALTHY = "healthy"
    STALE = "stale"


class CredentialState(StrEnum):
    """Why the TS5 gate admits or refuses a run; the value leads the slot record's detail."""

    PROVISIONED = "provisioned"
    NO_SECRETREF = "no_secretref"                      # the project declares no credential
    SECRETREF_WITHOUT_VALUE = "secretref_without_value"  # declared, but no value is set
    TARGET_OUTSIDE_DOMAINS = "target_outside_domains"  # a value, but not for this target


class RunVia(StrEnum):
    """Which surface asked for a run (`Run.via`); `None` means the original UI Run button."""

    TEAM_BUTTON = "team_button"


class SourceOriginKind(StrEnum):
    """Where a `Source` came from (`Source.origin`); `None` means it predates provenance.

    The members are the contract's own example set (TF6: upload | zip | drive | recording);
    T-198's detail models (`schema/intake.py` UploadOrigin/ZipOrigin/DriveOrigin) use these
    members as their `kind` discriminator, so the kinds are defined once, here."""

    UPLOAD = "upload"
    ZIP = "zip"
    DRIVE = "drive"
    RECORDING = "recording"
