"""Typed convenience over `filestore` for one project's directory (C1/C3)."""

from __future__ import annotations

from pathlib import Path

from autotester.core.paths import ProjectPaths
from autotester.schema.analysis import VideoAnalysis
from autotester.schema.approval import RunApproval
from autotester.schema.bench import BenchCorpus, BenchTrial
from autotester.schema.case import Case, CasePriority, CaseProposal
from autotester.schema.enums import ReviewStatus
from autotester.schema.flowspec import FlowSpec
from autotester.schema.issue import Issue
from autotester.schema.media import MediaPrep, Transcript
from autotester.schema.observation import ModelObservation
from autotester.schema.portal_persona import PortalPersona
from autotester.schema.project import Project, Source
from autotester.schema.run import RawResult, Run
from autotester.schema.screenmap import ScreenMap
from autotester.schema.verdict import Rubric, Verdict
from autotester.store.approval_revocations import load_unrevoked
from autotester.store.crawl_store import CrawlStoreMixin
from autotester.store.filestore import (
    append_jsonl,
    delete_jsonl_row,
    read_json,
    read_jsonl,
    upsert_jsonl,
    write_json,
)
from autotester.store.request_store import RequestStoreMixin
from autotester.store.run_store import RUN_AUX_FILES, RunStoreMixin


class PinnedCaseError(RuntimeError):
    """AT-585: delete refuses pinned cases; explicitly unpin via update_case first."""


class ProjectStore(CrawlStoreMixin, RequestStoreMixin, RunStoreMixin):
    """Human-editable artifacts (C6); AT-024 caches add ids, while list reads fresh."""

    def __init__(self, slug: str, root: Path | None = None) -> None:
        self.paths = ProjectPaths(slug, root)
        self._source_ids: set[str] | None = None
        self._case_ids: set[str] | None = None
        self._request_ids: set[str] | None = None
        self._issue_ids: set[str] | None = None
        self._node_ids: dict[str, set[str]] | None = None  # keyed by crawl_id

    def save_project(self, project: Project) -> None:
        write_json(self.paths.config, project)

    def load_project(self) -> Project | None:
        return read_json(self.paths.config, Project)

    def add_source(self, source: Source) -> Source:
        """Idempotent: re-adding an identical source is a no-op, not a duplicate."""
        if self._source_ids is None:
            self._source_ids = {s.id for s in self.list_sources()}
        if source.id in self._source_ids:
            return source
        append_jsonl(self.paths.sources_index, source)
        self._source_ids.add(source.id)
        return source

    def list_sources(self) -> list[Source]:
        return read_jsonl(self.paths.sources_index, Source)

    def add_approval(self, approval: RunApproval) -> RunApproval:
        append_jsonl(self.paths.approvals, approval)
        return approval

    def list_approvals(self) -> list[RunApproval]:
        return load_unrevoked(self.paths)

    def save_flowspec(self, spec: FlowSpec) -> None:
        write_json(self.paths.flowspec, spec)

    def load_flowspec(self) -> FlowSpec | None:
        return read_json(self.paths.flowspec, FlowSpec)

    def add_case(self, case: Case) -> Case:
        """Idempotent on id: regenerating a flowspec never duplicates a case."""
        if self._case_ids is None:
            self._case_ids = {c.id for c in self.list_cases()}
        if case.id in self._case_ids:
            return case
        append_jsonl(self.paths.cases, case)
        self._case_ids.add(case.id)
        return case

    def list_cases(self, priorities: list[CasePriority] | None = None) -> list[Case]:
        """File order, optionally selected priorities plus every pinned p0, once per id."""
        rows = read_jsonl(self.paths.cases, Case)
        if priorities is None:
            return rows
        if any(p not in {"p0", "p1", "p2", "p3"} for p in priorities):
            raise ValueError("unknown case priority")
        return list({c.id: c for c in rows if c.pinned or c.priority in priorities}.values())

    def get_case(self, case_id: str) -> Case | None:
        return next((c for c in self.list_cases() if c.id == case_id), None)

    def has_case(self, case_id: str) -> bool:
        """Cached add-time existence; callers can distinguish created from already present."""
        if self._case_ids is None:
            self._case_ids = {c.id for c in self.list_cases()}
        return case_id in self._case_ids

    def update_case(self, case: Case) -> None:
        """Replace by id; only fields outside compute_id can change without a new case."""
        upsert_jsonl(self.paths.cases, case, Case)
        if self._case_ids is not None:
            self._case_ids.add(case.id)

    def delete_case(self, case_id: str) -> bool:
        """Remove a case; AT-585 refuses pinned cases. Past runs/verdicts stay."""
        case = self.get_case(case_id)
        if case is not None and case.pinned:
            raise PinnedCaseError(
                f"case '{case_id}' is pinned (issue {case.pinned_issue_id}) and cannot be pruned")
        removed = delete_jsonl_row(self.paths.cases, Case, case_id)
        if removed and self._case_ids is not None:
            self._case_ids.discard(case_id)
        return removed

    def list_case_proposals(self) -> list[CaseProposal]:
        return read_jsonl(self.paths.case_proposals, CaseProposal)

    def stage_case_proposals(self, proposals: list[CaseProposal]) -> None:
        """Persist only fresh candidates; identical ids retain their human decisions."""
        spec = self.load_flowspec()
        if spec is None or spec.project != self.paths.slug:
            raise ValueError("save this project's FlowSpec before staging proposals")
        existing = {p.id for p in self.list_case_proposals()}
        proposals = [CaseProposal.model_validate(p.model_dump()) for p in proposals]
        if len({p.slot_id for p in proposals}) != len(proposals):
            raise ValueError("duplicate proposal slot in staged batch")
        for proposal in proposals:
            proposal.require_current(spec)
            if proposal.status != "proposed":
                raise ValueError("staging cannot grant proposal approval")
        for proposal in proposals:
            if proposal.id not in existing:
                upsert_jsonl(self.paths.case_proposals, proposal, CaseProposal, key="slot_id")
                existing.add(proposal.id)

    def review_case_proposal(self, proposal_id: str, by: str, approved: bool) -> CaseProposal:
        """Human review of an existing current row; pruning HAPPY persists pending."""
        proposal = next((p for p in self.list_case_proposals() if p.id == proposal_id), None)
        spec = self.load_flowspec()
        if proposal is None or spec is None or spec.project != self.paths.slug:
            raise ValueError("no current proposal to review")
        proposal.require_current(spec)
        reviewed = proposal.reviewed(by, approved)
        upsert_jsonl(self.paths.case_proposals, reviewed, CaseProposal)
        return reviewed

    def preflight_case_proposals(self, spec: FlowSpec, proposal_ids: list[str] | None = None,
                                flow_id: str | None = None) -> list[CaseProposal]:
        """Resolve saved approvals and the entire batch before any provider spend."""
        saved = self.load_flowspec()
        if (saved != spec or spec.project != self.paths.slug
                or spec.review.status != ReviewStatus.APPROVED):
            raise ValueError("generation requires the exact current approved saved FlowSpec")
        return CaseProposal.approved_batch(spec, self.list_case_proposals(), proposal_ids, flow_id)

    def save_rubric(self, rubric: Rubric) -> None:
        write_json(self.paths.rubrics_dir / f"{rubric.id}.json", rubric)

    def load_rubric(self, rubric_id: str) -> Rubric | None:
        return read_json(self.paths.rubrics_dir / f"{rubric_id}.json", Rubric)

    def save_run(self, run: Run) -> None:
        write_json(self.paths.run_dir(run.id) / "run.json", run)

    def load_run(self, run_id: str) -> Run | None:
        return read_json(self.paths.run_dir(run_id) / "run.json", Run)

    def save_result(self, run_id: str, result: RawResult) -> None:
        write_json(self.paths.run_dir(run_id) / f"{result.case_id}.json", result)

    def load_results(self, run_id: str) -> list[RawResult]:
        run_dir = self.paths.run_dir(run_id)
        if not run_dir.exists():
            return []
        return [model for path in sorted(run_dir.glob("*.json"))
            if path.name not in RUN_AUX_FILES and not path.name.endswith(".verdict.json")
            for model in [read_json(path, RawResult)] if model is not None]

    def save_verdict(self, run_id: str, verdict: Verdict) -> None:
        write_json(self.paths.run_dir(run_id) / f"{verdict.case_id}.verdict.json", verdict)

    def load_verdicts(self, run_id: str) -> list[Verdict]:
        run_dir = self.paths.run_dir(run_id)
        if not run_dir.exists():
            return []
        return [model for path in sorted(run_dir.glob("*.verdict.json"))
                for model in [read_json(path, Verdict)] if model is not None]

    def save_bench_corpus(self, corpus: BenchCorpus) -> None:
        write_json(self.paths.bench_corpus(corpus.id), corpus)

    def load_bench_corpus(self, corpus_id: str) -> BenchCorpus | None:
        return read_json(self.paths.bench_corpus(corpus_id), BenchCorpus)

    def save_bench_trial(self, trial: BenchTrial) -> None:
        write_json(self.paths.bench_trial(trial.id), trial)

    def list_bench_trials(self, corpus_id: str) -> list[BenchTrial]:
        bench_dir = self.paths.bench_dir
        if not bench_dir.exists():
            return []
        trials = [
            model
            for path in sorted(bench_dir.glob("*.trial.json"))
            for model in [read_json(path, BenchTrial)]
            if model is not None
        ]
        return [t for t in trials if t.corpus_id == corpus_id]

    def save_media_prep(self, prep: MediaPrep) -> None:
        write_json(self.paths.source_media(prep.source_id), prep)

    def load_media_prep(self, source_id: str) -> MediaPrep | None:
        return read_json(self.paths.source_media(source_id), MediaPrep)

    def save_transcript(self, transcript: Transcript) -> None:
        write_json(self.paths.source_transcript(transcript.source_id), transcript)

    def load_transcript(self, source_id: str) -> Transcript | None:
        return read_json(self.paths.source_transcript(source_id), Transcript)

    def save_observation(self, observation: ModelObservation) -> None:
        path = self.paths.source_observation(
            observation.source_id, observation.provider_label,
            observation.prompt_name, observation.chunk_index,
        )
        write_json(path, observation)

    def list_observations(self, source_id: str,
                          *, skip_unreadable: bool = False) -> list[ModelObservation]:
        """Cached answers; skip_unreadable lets analyze repair torn files by re-requesting."""
        obs_dir = self.paths.source_observations_dir(source_id)
        if not obs_dir.exists():
            return []
        found: list[ModelObservation] = []
        for path in sorted(obs_dir.glob("*.json")):
            try:
                model = read_json(path, ModelObservation)
            except Exception:
                if not skip_unreadable:
                    raise
                continue
            if model is not None:
                found.append(model)
        return found

    def save_analysis(self, analysis: VideoAnalysis) -> None:
        write_json(self.paths.source_analysis(analysis.source_id), analysis)

    def load_analysis(self, source_id: str) -> VideoAnalysis | None:
        return read_json(self.paths.source_analysis(source_id), VideoAnalysis)

    def add_issue(self, issue: Issue) -> Issue:
        """Idempotent on id, same lazy-cache pattern as `add_case`/`add_source`."""
        if self._issue_ids is None:
            self._issue_ids = {i.id for i in self.list_issues()}
        if issue.id in self._issue_ids:
            return issue
        append_jsonl(self.paths.issues, issue)
        self._issue_ids.add(issue.id)
        return issue

    def list_issues(self) -> list[Issue]:
        return read_jsonl(self.paths.issues, Issue)

    def update_issue(self, issue: Issue) -> None:
        upsert_jsonl(self.paths.issues, issue, Issue)
        if self._issue_ids is not None:
            self._issue_ids.add(issue.id)

    def delete_issue(self, issue_id: str) -> bool:
        removed = delete_jsonl_row(self.paths.issues, Issue, issue_id)
        if removed and self._issue_ids is not None:
            self._issue_ids.discard(issue_id)
        return removed

    def save_screen_map(self, screen_map: ScreenMap) -> None:
        write_json(self.paths.screen_map, screen_map)

    def load_screen_map(self) -> ScreenMap | None:
        return read_json(self.paths.screen_map, ScreenMap)

    def save_portal_persona(self, persona: PortalPersona) -> None:
        write_json(self.paths.portal_persona, persona)

    def load_portal_persona(self) -> PortalPersona | None:
        return read_json(self.paths.portal_persona, PortalPersona)
