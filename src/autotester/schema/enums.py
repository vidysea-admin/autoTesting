"""Every closed vocabulary in the system. Nothing else defines these strings."""

from __future__ import annotations

from enum import StrEnum

from autotester.schema.issue_kind import IssueKind  # noqa: F401 -- re-exported (AT-600)


class SourceKind(StrEnum):
    VIDEO = "video"
    DOC = "doc"
    TEXT = "text"
    AUDIO = "audio"
    EMAIL = "email"
    DRIVE = "drive"
    URL = "url"
    EVAL = "eval"
    CONDITION = "condition"
    USE_CASE = "use_case"


class Action(StrEnum):
    """What a step does to the browser.

    BACK/HOVER/PRESS_KEY/SCROLL discharge D-005's approved-but-unbuilt Action
    amendment (D-014); they exist for the Track B explorer (`stages/explore.py`)
    and are shared here rather than duplicated (C3).
    """

    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    UPLOAD = "upload"
    WAIT = "wait"
    ASSERT = "assert"
    BACK = "back"
    HOVER = "hover"
    PRESS_KEY = "press_key"
    SCROLL = "scroll"


class CaseKind(StrEnum):
    """Coarse bucket a case belongs to."""

    BEST = "best"
    WORST = "worst"
    EDGE = "edge"
    ANCHOR = "anchor"


class CaseClass(StrEnum):
    """The edge-case taxonomy — the product's differentiator.

    Expansion guarantees at least one case per applicable class per flow, so the
    agent cannot drift to the happy path alone.
    """

    HAPPY = "happy"
    AUTH_WRONG_CREDS = "auth_wrong_creds"
    AUTH_EXPIRED_SESSION = "auth_expired_session"
    SERVER_ERROR = "server_error"
    NETWORK_OFFLINE_SLOW = "network_offline_slow"
    INPUT_EMPTY = "input_empty"
    INPUT_BOUNDARY = "input_boundary"
    INPUT_UNICODE_OVERSIZE = "input_unicode_oversize"
    DOUBLE_SUBMIT = "double_submit"
    BACK_REFRESH_MIDFLOW = "back_refresh_midflow"
    DEEPLINK_UNAUTH = "deeplink_unauth"
    CONCURRENT_TAB = "concurrent_tab"
    LOCALE_I18N = "locale_i18n"
    VIEWPORT_MOBILE = "viewport_mobile"
    REGRESSION_ANCHOR = "regression_anchor"


KIND_BY_CLASS: dict[CaseClass, CaseKind] = {
    CaseClass.HAPPY: CaseKind.BEST,
    CaseClass.AUTH_WRONG_CREDS: CaseKind.WORST,
    CaseClass.AUTH_EXPIRED_SESSION: CaseKind.WORST,
    CaseClass.SERVER_ERROR: CaseKind.WORST,
    CaseClass.NETWORK_OFFLINE_SLOW: CaseKind.WORST,
    CaseClass.INPUT_EMPTY: CaseKind.EDGE,
    CaseClass.INPUT_BOUNDARY: CaseKind.EDGE,
    CaseClass.INPUT_UNICODE_OVERSIZE: CaseKind.EDGE,
    CaseClass.DOUBLE_SUBMIT: CaseKind.EDGE,
    CaseClass.BACK_REFRESH_MIDFLOW: CaseKind.EDGE,
    CaseClass.DEEPLINK_UNAUTH: CaseKind.EDGE,
    CaseClass.CONCURRENT_TAB: CaseKind.EDGE,
    CaseClass.LOCALE_I18N: CaseKind.EDGE,
    CaseClass.VIEWPORT_MOBILE: CaseKind.EDGE,
    CaseClass.REGRESSION_ANCHOR: CaseKind.ANCHOR,
}


class Severity(StrEnum):
    S1 = "S1"  # blocks a core flow
    S2 = "S2"  # degrades a flow, workaround exists
    S3 = "S3"  # cosmetic or minor


class CaseStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    RETIRED = "retired"


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    NEEDS_EDIT = "needs_edit"


class Outcome(StrEnum):
    """What the executor observed — NOT a judgement. Grading is separate."""

    COMPLETED = "completed"
    ERRORED = "errored"
    BLOCKED_HITL = "blocked_hitl"
    ASSERTION_FAILED = "assertion_failed"
    """D-032/AT-540: a step's declared expectation (or an Action.ASSERT
    step's expected state) deterministically did not hold at settle time.
    An OBSERVATION, not a grade — the grader still owns the verdict."""

    NOT_RUN = "not_run"
    """D-045/AT-581/E6: condition not enacted; case did not run -- must never be judged PASS."""


class Result(StrEnum):
    """The grader's verdict. Only the grader writes this."""

    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    INCONCLUSIVE = "INCONCLUSIVE"


class EvidenceKind(StrEnum):
    SCREENSHOT = "screenshot"
    DOM = "dom"
    URL = "url"
    NETWORK = "network"
    TRACE = "trace"
    CONSOLE = "console"
    DB = "db"


class Trigger(StrEnum):
    MANUAL = "manual"
    CI = "ci"
    SCHEDULE = "schedule"


class WritePolicy(StrEnum):
    """How much the tester is allowed to mutate in the target app."""

    READ_ONLY = "read_only"
    TEST_ACCOUNT = "test_account"
    ALLOW_WRITES = "allow_writes"


class ApprovalKind(StrEnum):
    """What a `RunApproval` authorises. D-018's two gates: READ is gate 1 (scope
    of read access); everything else is gate 2 (an outward-facing run)."""

    READ = "read"
    CRAWL = "crawl"
    ADVERSARIAL = "adversarial"
    LIVE_CASE = "live_case"


class ProviderRole(StrEnum):
    VISION = "vision"
    AGENT = "agent"
    JUDGE = "judge"


class RequestStatus(StrEnum):
    OPEN = "open"
    FULFILLED = "fulfilled"
    DISMISSED = "dismissed"


class Participant(StrEnum):
    HUMAN = "human"
    AUTOTESTER = "autotester"


class FeatureEventKind(StrEnum):
    """What happened to a feature, as recorded in `docs/FEATURES.jsonl`."""

    PLANNED = "planned"
    LIVE = "live"
    UPDATED = "updated"
    RETIRED = "retired"


class UserValue(StrEnum):
    """How much the product's user depends on a feature. Gates the reasoning ask."""

    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class IssueCategory(StrEnum):
    """What kind of problem a video-derived `Issue` is. The first 12 come from the
    proven external pipeline's bug taxonomy; `FEATURE_GAP`/`WRONG_MODEL`/`DATA_ERROR`
    were added for D-014 after a real ground-truth workbook showed 10/33 rows were
    spoken change requests with no home in the original 12 ("this should be X")."""

    VALIDATION = "validation"
    LAYOUT = "layout"
    DEAD_END = "dead_end"
    LATENCY = "latency"
    BROKEN_LINK = "broken_link"
    COPY_TEXT = "copy_text"
    STATE_LOSS = "state_loss"
    DATA_INCONSISTENCY = "data_inconsistency"
    TRANSIENT_GLITCH = "transient_glitch"
    NAVIGATION_CONFUSION = "navigation_confusion"
    LOGIC_ERROR = "logic_error"
    FEATURE_GAP = "feature_gap"
    WRONG_MODEL = "wrong_model"
    DATA_ERROR = "data_error"
    OTHER = "other"


class IssueOrigin(StrEnum):
    """How an `Issue` was noticed — mirrors the human sheet's 'How we know'."""

    SPOKEN = "spoken"
    SCREEN = "screen"
    SPOKEN_AND_SCREEN = "spoken_and_screen"
    MODEL_DETECTED = "model_detected"


class IssueStatus(StrEnum):
    OPEN = "open"
    CONFIRMED = "confirmed"
    FIXED = "fixed"
    DISMISSED = "dismissed"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class NodeStatus(StrEnum):
    """A crawled screen's state in the BFS frontier (Track B)."""

    QUEUED = "queued"
    EXPLORED = "explored"
    ABORTED_DIALOG = "aborted_dialog"
    ABORTED_ERROR = "aborted_error"


class EdgeOutcome(StrEnum):
    """What happened when the explorer tried one candidate action."""

    NAVIGATED = "navigated"
    SAME_SCREEN = "same_screen"
    DENIED_POLICY = "denied_policy"
    SKIPPED_UNNAMED = "skipped_unnamed"
    OFF_DOMAIN_REFUSED = "off_domain_refused"
    DIALOG = "dialog"
    ERRORED = "errored"


class CrawlStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED_BOUND = "stopped_bound"
    LOGIN_FAILED = "login_failed"
    ABORTED = "aborted"
    BLOCKED_NO_ACTIONS = "blocked_no_actions"
    """AT-242: the frontier emptied with every reachable action refused by policy
    (denied > 0) and none performed (actions_used == 0). Distinct from COMPLETED
    (nothing denied is genuinely explored) and LOGIN_FAILED (login didn't complete)."""
    LOGIN_WALL = "login_wall"
    """X18/AT-458: no login case declared, every screen ends in a refused form
    submit, no link led anywhere structurally different — the crawl met a
    sign-in wall and saw nothing behind it. Never success."""
