"""Filesystem layout. The ONLY place project paths are constructed.

Every artifact lives under `projects/<slug>/` as a human-readable file. Nothing
in the system may build these paths by string concatenation elsewhere.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

ENV_ROOT = "AUTOTESTER_ROOT"

def repo_root() -> Path:
    """Repository root; overridable via `AUTOTESTER_ROOT` (used by tests)."""
    override = os.environ.get(ENV_ROOT)
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[3]

class ProjectPaths:
    """Resolved paths for one project. Construct with a slug, ask for what you need."""

    def __init__(self, slug: str, root: Path | None = None) -> None:
        self.slug = slug
        self.root = root or repo_root()

    @property
    def dir(self) -> Path:
        return self.root / "projects" / self.slug
    @property
    def config(self) -> Path:
        return self.dir / "project.json"
    @property
    def approvals(self) -> Path:
        """Append-only human-granted RunApproval rows (D-018)."""
        return self.dir / "approvals.jsonl"
    @property
    def env_file(self) -> Path:
        """One root credential file; projects resolve only their namespaced SecretRefs."""
        return self.root / ".env"
    @property
    def sources_dir(self) -> Path:
        return self.dir / "sources"
    @property
    def sources_index(self) -> Path:
        return self.dir / "sources.jsonl"
    @property
    def flowspec(self) -> Path:
        return self.dir / "flowspec.json"
    @property
    def cases(self) -> Path:
        return self.dir / "cases.jsonl"
    @property
    def rubrics_dir(self) -> Path:
        return self.dir / "rubrics"
    @property
    def scripts_dir(self) -> Path:
        return self.dir / "scripts"
    @property
    def runs_dir(self) -> Path:
        return self.dir / "runs"
    @property
    def requests(self) -> Path:
        return self.dir / "requests.jsonl"
    @property
    def knowledge(self) -> Path:
        return self.dir / "knowledge.md"
    @property
    def portal_persona(self) -> Path:
        """The durable cross-run product model (T-164). One JSON file per
        project; `knowledge` is its regenerated human-readable view."""
        return self.dir / "portal_persona.json"
    @property
    def user_personas(self) -> Path:
        """T-190: advisory `UserPersona` rows, one per line (id-keyed)."""
        return self.dir / "user_personas.jsonl"
    @property
    def bench_dir(self) -> Path:
        return self.dir / "bench"
    def bench_corpus(self, corpus_id: str) -> Path:
        return self.bench_dir / f"{corpus_id}.json"
    def bench_trial(self, trial_id: str) -> Path:
        return self.bench_dir / f"{trial_id}.trial.json"
    @property
    def profile_dir(self) -> Path:
        """Persistent browser profile — gitignored, holds the logged-in session."""
        return self.root / "profiles" / self.slug
    def run_dir(self, run_id: str) -> Path:
        return self.runs_dir / run_id
    def bundles_dir(self, run_id: str) -> Path:
        """Where a run's failure bundles live (T-178); each is one directory."""
        return self.run_dir(run_id) / "bundles"
    def run_trace(self, run_id: str) -> Path:
        """The redacted per-run trace (D-041 phase 1, RT1) -- `trace_id`
        equals `run_id`, never re-minted (RT2)."""
        return self.run_dir(run_id) / "trace.jsonl"
    def run_ux_report(self, run_id: str) -> Path:
        """T-190/PU2: the run's advisory UX findings -- beside, never in, a case result."""
        return self.run_dir(run_id) / "ux_report.json"
    # -- Track A: video learning (D-014) ---------------------------------------
    def source_dir(self, source_id: str) -> Path:
        return self.dir / "sources" / source_id
    def source_media(self, source_id: str) -> Path:
        return self.source_dir(source_id) / "media.json"

    def source_transcript(self, source_id: str) -> Path:
        return self.source_dir(source_id) / "transcript.json"

    def source_chunks_dir(self, source_id: str) -> Path:
        return self.source_dir(source_id) / "chunks"

    def source_frames_dir(self, source_id: str) -> Path:
        return self.source_dir(source_id) / "frames"

    def source_observations_dir(self, source_id: str) -> Path:
        return self.source_dir(source_id) / "observations"

    def source_observation(
        self, source_id: str, provider_label: str, prompt_name: str, chunk_index: int
    ) -> Path:
        label = provider_label.replace(":", "_").replace("/", "_")
        name = f"{label}__{prompt_name}__{chunk_index:02d}.json"
        return self.source_observations_dir(source_id) / name

    def source_analysis(self, source_id: str) -> Path:
        return self.source_dir(source_id) / "analysis.json"

    @property
    def issues(self) -> Path:
        return self.dir / "issues.jsonl"

    @property
    def screen_map(self) -> Path:
        return self.dir / "screenmap.json"

    # -- Track B: autonomous explorer (D-015) ----------------------------------
    @property
    def crawls_dir(self) -> Path:
        return self.dir / "crawl"

    def crawl_dir(self, crawl_id: str) -> Path:
        return self.crawls_dir / crawl_id

    def crawl_shots_dir(self, crawl_id: str) -> Path:
        return self.crawl_dir(crawl_id) / "shots"

    def crawl_nodes(self, crawl_id: str) -> Path:
        return self.crawl_dir(crawl_id) / "nodes.jsonl"

    def crawl_edges(self, crawl_id: str) -> Path:
        return self.crawl_dir(crawl_id) / "edges.jsonl"

    def crawl_issues(self, crawl_id: str) -> Path:
        return self.crawl_dir(crawl_id) / "issues.jsonl"

    def crawl_network(self, crawl_id: str) -> Path:
        """T-170/NA1: first-party NETWORK evidence captured during the crawl."""
        return self.crawl_dir(crawl_id) / "network.jsonl"

    def crawl_frontier(self, crawl_id: str) -> Path:
        return self.crawl_dir(crawl_id) / "frontier.json"

    def crawl_manifest(self, crawl_id: str) -> Path:
        return self.crawl_dir(crawl_id) / "crawl.json"

    def ensure(self) -> None:
        """Create the directories a project needs. Safe to call repeatedly."""
        for path in (
            self.dir,
            self.sources_dir,
            self.rubrics_dir,
            self.scripts_dir,
            self.runs_dir,
            self.profile_dir,
            self.bench_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def work_dir(root: Path | None = None) -> Path:
    """Scratch space. Nothing here is committed; nothing outside here is scratch."""
    path = (root or repo_root()) / ".work"
    path.mkdir(parents=True, exist_ok=True)
    return path


class RepoDocs:
    """Repo-level documents: the living map, the ledger, the history, the router."""

    def __init__(self, root: Path | None = None, *, prompts_dir: Path | None = None,
                 skills_dir: Path | None = None) -> None:
        self.root = root or repo_root()
        self._root_given = root is not None
        self._prompts_dir_override = prompts_dir
        self._skills_dir_override = skills_dir

    @property
    def docs_dir(self) -> Path:
        return self.root / "docs"

    @property
    def architecture(self) -> Path:
        return self.docs_dir / "ARCHITECTURE.md"

    @property
    def snapshot(self) -> Path:
        return self.docs_dir / "SNAPSHOT.md"

    @property
    def map(self) -> Path:
        """Generated directory map + schema summary (kept out of ARCHITECTURE's 150-line budget)."""
        return self.docs_dir / "MAP.md"

    @property
    def features(self) -> Path:
        return self.docs_dir / "FEATURES.jsonl"

    @property
    def decisions(self) -> Path:
        return self.docs_dir / "DECISIONS.md"

    @property
    def router(self) -> Path:
        """`CLAUDE.md` carries the "open X when Y" table."""
        return self.root / "CLAUDE.md"

    @property
    def goal(self) -> Path:
        return self.root / ".goal" / "goal.json"

    @property
    def prompts_dir(self) -> Path:
        """Prompts ship with code. Explicit overrides and explicit root win;
        AUTOTESTER_ROOT relocates data only (AT-132/AT-137)."""
        if self._prompts_dir_override is not None:
            return self._prompts_dir_override
        if self._root_given:
            return self.root / "src" / "autotester" / "prompts"
        return Path(__file__).resolve().parents[1] / "prompts"

    @property
    def skills_dir(self) -> Path:
        """Skills ship with code, with the same explicit override rules as prompts."""
        if self._skills_dir_override is not None:
            return self._skills_dir_override
        if self._root_given:
            return self.root / "src" / "autotester" / "skills"
        return Path(__file__).resolve().parents[1] / "skills"

def team_component(value: str, *, slot: bool = False) -> str:
    """Validate one portable path component; encode safe slot keys without collisions."""
    if (not value or len(value) > 120 or value in {".", ".."} or ".." in value
            or any(c in value for c in "/\\\\") or value.endswith((".", " "))
            or re.match(r"^[A-Za-z]:", value) or value.startswith(("/", "\\\\"))
            or value.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL",
                                               *[f"COM{i}" for i in range(1, 10)],
                                               *[f"LPT{i}" for i in range(1, 10)]}):
        raise ValueError(f"unsafe team component: {value!r}")
    if slot:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
    if not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.@+-]*", value):
        raise ValueError(f"unsafe team component: {value!r}")
    return value


def team_path(*components: str, root: Path | None = None) -> Path:
    """The sole team-state path constructor under the data root, refusing symlink escape."""
    base = ((root or repo_root()).resolve() / ".work" / "team").resolve()
    candidate = base.joinpath(*(team_component(c) for c in components))
    data = (root or repo_root()).resolve()
    resolved, boundary = candidate.resolve(), data / ".work" / "team"
    if os.name == "nt":
        comparison = []
        for path in (resolved, boundary):
            text = str(path)
            if text.startswith("\\\\?\\"):
                if re.match(r"^[A-Za-z]:\\", text[4:]):
                    text = text[4:]
                elif text[4:8].upper() == "UNC\\":
                    text = "\\\\" + text[8:]
                else:
                    raise ValueError("team path escapes the data root")
            if text.startswith(("\\\\?\\", "\\\\.\\")):
                raise ValueError("team path escapes the data root")
            path = Path(text)
            unc = path.drive[2:].split("\\") if path.drive.startswith("\\\\") else []
            if not path.is_absolute() or not (
                re.fullmatch(r"[A-Za-z]:", path.drive)
                or (len(unc) == 2 and all(c and c not in {".", "..", "?"} for c in unc))
            ):
                raise ValueError("team path escapes the data root")
            comparison.append(path)
        resolved, boundary = comparison
    if not resolved.is_relative_to(boundary):
        raise ValueError("team path escapes the data root")
    return candidate
