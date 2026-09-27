"""Project configuration and the secret contract. One directory per project."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from autotester.schema.base import Artifact
from autotester.schema.enums import ProviderRole, SourceKind, WritePolicy

DEFAULT_VISION_PROVIDER = "gemini"
"""AT-550: the vision provider `vision_ensemble()` substitutes when the
configured `vision` string is empty. Named explicitly so the substitution
is a documented constant, not a bare literal buried in the fallback — and so
`vision_ensemble_defaulted()` below can tell callers when this happened."""


class SecretRef(BaseModel):
    """A declared credential. Holds the KEY and its scope — never the value.

    The value lives only in the repo-root `.env` and is substituted at the
    moment of typing into the browser, scoped to `domains`.
    """

    model_config = ConfigDict(extra="forbid")

    key: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    description: str | None = None
    domains: list[str] = Field(default_factory=list, description="hosts this may be typed into")
    mask_in_screenshot: bool = True

    @field_validator("key")
    @classmethod
    def _reject_value_like(cls, value: str) -> str:
        if len(value) > 64:
            raise ValueError("secret key looks like a value, not a name")
        return value

    @field_validator("domains")
    @classmethod
    def _reject_blank_domains(cls, domains: list[str]) -> list[str]:
        """A blank domain would match an empty host and open the gate (AT-001)."""
        cleaned = [d.strip().lower().lstrip(".") for d in domains]
        if any(not d for d in cleaned):
            raise ValueError("secret domains must be non-empty hostnames")
        return cleaned


class ProviderConfig(BaseModel):
    """Which provider serves each role. Roles are swappable per project.

    AT-542: `vision` may name SEVERAL providers, comma-separated
    (`"gemini,anthropic"`), which run as the video ensemble — the one place
    where agreement between independent readings is the signal itself
    (qa/contracts/video-learning.md). A single name is an ensemble of one and
    is exactly what the F-039 overstatement was: real agreement never ran.
    `for_role` returns the whole string; the analyze callers split it."""

    model_config = ConfigDict(extra="forbid")

    vision: str = "gemini"
    agent: str = "langchain-fallback"
    judge: str = "langchain-fallback"

    def for_role(self, role: ProviderRole) -> str:
        return getattr(self, str(role))

    def _configured_vision_providers(self) -> list[str]:
        """The vision provider ids explicitly named in `vision`, in order,
        deduplicated — empty when the config is blank/whitespace/commas
        only. No fallback here; shared by `vision_ensemble()` (which applies
        the default) and `vision_ensemble_defaulted()` (which reports
        whether it had to), so the parsing rule lives in exactly one place."""
        seen: list[str] = []
        for name in self.vision.split(","):
            name = name.strip()
            if name and name not in seen:
                seen.append(name)
        return seen

    def vision_ensemble(self) -> list[str]:
        """The vision provider ids in order, deduplicated — the ensemble the
        analyze callers run. One entry = ensemble of one (honest, not an
        error: a single credential must still work)."""
        return self._configured_vision_providers() or [DEFAULT_VISION_PROVIDER]

    def vision_ensemble_defaulted(self) -> bool:
        """AT-550: True when `vision` was empty and `vision_ensemble()`
        substituted `DEFAULT_VISION_PROVIDER` — distinct from an operator who
        explicitly configured that same single provider. An empty config
        falling back to a default must be observable, not silent; callers
        (`ui/routes_sources.py`, `cli_video.py`) record this alongside
        `requested_providers` on the persisted `VideoAnalysis` so a defaulted
        run is never indistinguishable from an explicit one."""
        return not self._configured_vision_providers()


class Source(Artifact):
    """An immutable input the system learned from."""

    id: str = ""
    project: str
    kind: SourceKind
    path: str | None = Field(default=None, description="project-relative, for video/doc")
    text: str | None = Field(default=None, description="inline body, for kind=text")
    url: str | None = None
    sha256: str | None = None
    duration_s: float | None = None
    label: str | None = None
    notes: str | None = None
    recorded_on: str | None = Field(
        default=None, description="ISO date, e.g. the Excel 'Date' column"
    )

    def model_post_init(self, _context: object) -> None:
        if not self.id:
            from autotester.core.ids import content_id

            key = self.sha256 or self.url or self.text or self.path or self.label
            object.__setattr__(self, "id", content_id("src", {"k": str(self.kind), "v": key}))


class Project(Artifact):
    """Everything the system needs to test one product."""

    slug: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    name: str
    base_url: str
    allowed_domains: list[str] = Field(
        default_factory=list,
        description="the browser may only be driven here; secrets scoped within",
    )
    write_policy: WritePolicy = WritePolicy.READ_ONLY
    max_parallel: int = Field(
        default=1, ge=1,
        description="ceiling on concurrently-running cases (T-173/D-041); the run's actual N "
                    "is min(this, a measured RAM/CPU budget) -- see stages/parallel_run.py",
    )
    secrets: list[SecretRef] = Field(default_factory=list)
    providers: ProviderConfig = Field(default_factory=ProviderConfig)
    headed: bool = Field(default=True, description="real visible browser by default")
    description: str | None = None
    login_case_id: str | None = Field(
        default=None,
        description="the case a crawl logs in with before exploring — declared once, here, "
                    "and used by every entry point (X17); None means the product is crawled "
                    "signed out",
    )

    def secret(self, key: str) -> SecretRef | None:
        return next((s for s in self.secrets if s.key == key), None)

    def allows_domain(self, host: str) -> bool:
        """True when `host` is the base host or an allowed domain (or subdomain)."""
        candidates = list(self.allowed_domains)
        return any(host == d or host.endswith(f".{d}") for d in candidates)
