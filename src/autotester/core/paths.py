"""Filesystem layout. The ONLY place project paths are constructed.

Every artifact lives under `projects/<slug>/` as a human-readable file. Nothing
in the system may build these paths by string concatenation elsewhere.
"""

from __future__ import annotations

import os
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
        """Human-granted `RunApproval` rows (D-018). Append-only in practice: an
        approval is never edited, it expires or a new one is granted."""
        return self.dir / "approvals.jsonl"

    @property
    def env_file(self) -> Path:
        """One credential file for the whole repo, at the root (Umesh, 2026-09-03).

        Keys are namespaced per project (`PATHLYNKS_*`) and declared in each
        project's `SecretRef[]`; a project can only resolve the keys it declares.
        """
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

    def run_trace(self, run_id: str) -> Path:
        """The redacted per-run trace (D-041 phase 1, RT1) -- `trace_id`
        equals `run_id`, never re-minted (RT2)."""
        return self.run_dir(run_id) / "trace.jsonl"

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
        """Prompts ship WITH THE CODE, so the DATA root must not move them.

        `root` falls back to `repo_root()`, which honours `AUTOTESTER_ROOT` — a
        switch for relocating a project's DATA. That silently moved the prompt
        lookup too, and `autotester ingest run` under a relocated root died on
        `FileNotFoundError: <data root>/src/autotester/prompts/...` (AT-132,
        found by a test driving the real CLI). Every prompt-reading stage was
        one environment variable away from the same failure.

        An EXPLICIT `root` still wins: substituting a stub prompt tree is a
        legitimate thing for a test to do, and the defect was never explicit
        injection — it was the env var leaking into a path it does not own.

        AT-137: that fallback used to be the ONLY way to substitute a prompt
        tree — an inferred side effect of passing `root`, not a named act.
        Pass `prompts_dir=` explicitly instead when that is what's meant;
        `root` alone still behaves exactly as before for every caller that
        never adopts the explicit form (no behaviour change, C2)."""
        if self._prompts_dir_override is not None:
            return self._prompts_dir_override
        if self._root_given:
            return self.root / "src" / "autotester" / "prompts"
        return Path(__file__).resolve().parents[1] / "prompts"

    @property
    def skills_dir(self) -> Path:
        """Migrated-prompt `SKILL.md` folders (T-175/D-041) -- same shape as
        `prompts_dir` above and for the same reason: ships WITH THE CODE, so an
        explicit override lets a test substitute a stub tree (mirroring
        AT-137's `prompts_dir=` fix) without a relocated `AUTOTESTER_ROOT`
        leaking into a path it does not own."""
        if self._skills_dir_override is not None:
            return self._skills_dir_override
        if self._root_given:
            return self.root / "src" / "autotester" / "skills"
        return Path(__file__).resolve().parents[1] / "skills"
