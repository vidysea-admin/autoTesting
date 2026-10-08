"""Group 10 closed vocabularies; pre-existing vocabularies remain in schema/enums.py."""

from enum import StrEnum


class SourceOrigin(StrEnum):
    UPLOAD = "upload"
    ZIP = "zip"
    DRIVE = "drive"
    RECORDING = "recording"


class QueueStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    REFUSED = "refused"
    INTERRUPTED = "interrupted"


class RunVia(StrEnum):
    BUTTON = "button"
    SCHEDULE = "schedule"
    API = "api"


class ScheduleMode(StrEnum):
    MANUAL = "manual"
    FIXED = "fixed"
    CUSTOM = "custom"


class SlotOutcome(StrEnum):
    ENQUEUED = "enqueued"
    MISSED = "missed"
    SKIPPED_OVERLAP = "skipped_overlap"
    BLOCKED_CREDENTIALS = "blocked_credentials"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
