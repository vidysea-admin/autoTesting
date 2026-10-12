"""Contract: qa/contracts/bench.md K1-K8. Independent score and storage oracles.
-- the real end-to-end trial (a real browser + a real judge) is not a
network-independent unit test by nature; see
qa/manifests/t120-bench.md for that real run's cited evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from autotester.schema.bench import BenchCorpus, BenchTrial, Finding, SeededBug
from autotester.schema.enums import Participant, Result, Severity
from autotester.schema.verdict import Failure, Verdict
from autotester.stages import bench
from autotester.store.project_store import ProjectStore


def _corpus() -> BenchCorpus:
    return BenchCorpus(
        id="corpus_test", app="demo", build_ref="broken", mode="fixture",
        seeded_bugs=[
            SeededBug(
                id="bug_login", description="login rejects correct password",
                location="/login.html", detect_hint="error on correct credentials",
                severity=Severity.S1, provenance="fixture_seeded",
            )
        ],
    )


def _verdict(case_id: str, result: Result, criterion_id: str = "c1") -> Verdict:
    return Verdict(
        run_id="run_1", case_id=case_id, result=result,
        failures=(
            [Failure(criterion_id=criterion_id, reason="broke")] if result is Result.FAIL else []
        ),
    )


def test_findings_from_verdicts_maps_a_fail_to_its_seeded_bug() -> None:
    verdicts = [_verdict("case_login", Result.FAIL)]
    findings = bench.findings_from_verdicts(verdicts, {"case_login": "bug_login"})
    assert len(findings) == 1
    assert findings[0].matched_bug_id == "bug_login"


def test_findings_from_verdicts_unmapped_fail_is_a_false_positive() -> None:
    verdicts = [_verdict("case_home", Result.FAIL)]
    findings = bench.findings_from_verdicts(verdicts, {"case_login": "bug_login"})
    assert findings[0].matched_bug_id is None


def test_findings_from_verdicts_ignores_pass_and_inconclusive() -> None:
    verdicts = [_verdict("case_login", Result.PASS), _verdict("case_home", Result.INCONCLUSIVE)]
    findings = bench.findings_from_verdicts(verdicts, {})
    assert findings == []


def test_run_autotester_trial_detects_the_seeded_bug() -> None:
    corpus = _corpus()
    verdicts = [_verdict("case_login", Result.FAIL)]
    trial = bench.run_autotester_trial(
        "trial_ai", corpus, verdicts, {"case_login": "bug_login"}, duration_s=12.0,
        ordering="independent_parallel",
    )
    assert trial.participant is Participant.AUTOTESTER
    score = trial.score(corpus)
    assert score["detected"] == 1
    assert score["false_positives"] == 0


def test_oracle_human_trial_is_labeled_a_baseline_not_a_live_run() -> None:
    corpus = _corpus()
    trial = bench.oracle_human_trial("trial_human", corpus)
    assert trial.participant is Participant.HUMAN
    assert trial.participant_label == "human-oracle-baseline"
    assert trial.kind == "human_oracle"
    assert trial.ordering == "independent_parallel"
    score = trial.score(corpus)
    assert score["detection_rate"] == 1.0
    assert score["false_positive_rate"] == 0.0


def test_oracle_human_trial_never_carries_a_hardcoded_duration() -> None:
    """K8: unmeasured time is None; a measured zero remains a number."""
    corpus = _corpus()
    trial = bench.oracle_human_trial("trial_human", corpus)
    assert trial.duration_s is None
    assert trial.score(corpus)["duration_s"] is None
    timed = bench.oracle_human_trial("trial_human_timed", corpus, duration_s=142.5)
    assert timed.duration_s == 142.5


def _live_corpus() -> BenchCorpus:
    rows = [("high", Severity.S1, "human_independent"),
            ("low", Severity.S3, "human_independent"),
            ("prompt", Severity.S2, "human_prompted")]
    return BenchCorpus(
        id="live", app="demo", build_ref="real-build", mode="human_confirmed",
        seeded_bugs=[SeededBug(id=key, description=key, severity=severity,
                              location="/" + key, detect_hint=key, provenance=source)
                     for key, severity, source in rows],
    )


def _trial(corpus: BenchCorpus, **changes) -> BenchTrial:
    values = dict(id="trial", corpus_id=corpus.id, participant=Participant.HUMAN,
                  kind="human_live", ordering="independent_parallel")
    values.update(changes)
    return BenchTrial(**values)


def test_live_machine_denominator_excludes_prompted_truth() -> None:
    corpus = _live_corpus()
    trial = _trial(corpus, participant=Participant.AUTOTESTER, kind="autotester",
                   findings=[Finding(text="high", matched_bug_id="high"),
                             Finding(text="prompt", matched_bug_id="prompt")])
    score = trial.score(corpus)
    assert score["detected"] == 1, "only independently confirmed live truth counts"
    assert score["detection_rate"] == pytest.approx(1 / 2)
    assert score["severity_weighted_recall"] == pytest.approx(3 / 4)


def test_unknown_truth_prevents_independent_recall_even_with_known_subset() -> None:
    corpus = _live_corpus()
    corpus.seeded_bugs.append(SeededBug(id="unsure", description="unconfirmed",
                                      location="/unsure", detect_hint="unsure"))
    trial = _trial(corpus, findings=[Finding(text="low", matched_bug_id="low",
                                           provenance="independent")])
    score = trial.score(corpus)
    assert score["severity_weighted_recall"] is None
    assert score["severity_weighted_recall_unavailable_reason"]


def test_prompted_human_findings_do_not_inflate_recall_but_fp_uses_all_reports() -> None:
    corpus = _live_corpus()
    findings = [Finding(text="low", matched_bug_id="low", provenance="independent"),
                Finding(text="high", matched_bug_id="high", provenance="prompted"),
                Finding(text="false", provenance="prompted")]
    score = _trial(corpus, ordering="human_read_ai_first", findings=findings).score(corpus)
    assert score["detected"] == 1, "prompted high-severity report cannot earn recall"
    assert score["detection_rate"] == pytest.approx(1 / 2)
    assert score["severity_weighted_recall"] == pytest.approx(1 / 4)
    assert score["false_positives"] == 1
    assert score["false_positive_rate"] == pytest.approx(1 / 3)
    assert score["false_positive_population"] == "all_reported_findings"


@pytest.mark.parametrize("ordering", ["unknown", "ai_read_human_first"])
def test_machine_recall_unavailable_when_ordering_cannot_establish_independence(ordering):
    corpus = _live_corpus()
    trial = _trial(corpus, participant=Participant.AUTOTESTER, kind="autotester",
                   ordering=ordering, findings=[Finding(text="high", matched_bug_id="high")])
    score = trial.score(corpus)
    assert score["severity_weighted_recall"] is None
    assert score["severity_weighted_recall_unavailable_reason"]


def test_legacy_missing_metadata_is_unknown_and_measurements_are_unavailable() -> None:
    corpus = BenchCorpus.model_validate(dict(id="legacy", app="demo", build_ref="old"))
    trial = BenchTrial.model_validate(dict(id="old", corpus_id="legacy",
                                         participant="human", findings=[{"text": "claim"}]))
    assert corpus.mode == "unknown"
    assert trial.kind == "unknown"
    assert trial.ordering == "unknown"
    assert trial.findings[0].provenance == "unknown"
    score = trial.score(corpus)
    assert score["detection_rate"] is None
    assert score["severity_weighted_recall"] is None
    assert score["duration_s"] is None
    assert score["severity_weighted_recall_unavailable_reason"]


def test_empty_reports_have_no_fp_measurement_and_measured_zero_time_is_preserved() -> None:
    corpus = _live_corpus()
    score = _trial(corpus, duration_s=0.0).score(corpus)
    assert score["false_positive_rate"] is None
    assert score["false_positive_rate_unavailable_reason"]
    assert score["duration_s"] == 0.0
    assert score["severity_weighted_recall"] == 0.0, "measured no detection is a real zero"


def test_unknown_human_finding_does_not_become_independent_by_default() -> None:
    corpus = _live_corpus()
    score = _trial(corpus, findings=[Finding(text="high", matched_bug_id="high")]).score(corpus)
    assert score["severity_weighted_recall"] is None
    assert score["severity_weighted_recall_unavailable_reason"] == (
        "human finding provenance not recorded"
    )


def test_project_store_roundtrip_preserves_provenance_and_nullable_time(tmp_path: Path) -> None:
    corpus = _live_corpus()
    trial = _trial(corpus, ordering="human_read_ai_first",
                   findings=[Finding(text="low", matched_bug_id="low", provenance="independent"),
                             Finding(text="high", matched_bug_id="high", provenance="prompted")])
    store = ProjectStore("bench-test", root=tmp_path)
    store.save_bench_corpus(corpus)
    store.save_bench_trial(trial)
    assert store.load_bench_corpus(corpus.id) == corpus
    loaded_trials = store.list_bench_trials(corpus.id)
    assert loaded_trials == [trial]
    assert loaded_trials[0].duration_s is None
    saved = json.loads(store.paths.bench_trial(trial.id).read_text(encoding="utf-8"))
    truth = json.loads(store.paths.bench_corpus(corpus.id).read_text(encoding="utf-8"))
    assert saved["kind"] == "human_live"
    assert saved["ordering"] == "human_read_ai_first"
    assert saved.get("duration_s") is None
    assert [row["provenance"] for row in saved["findings"]] == ["independent", "prompted"]
    assert truth["mode"] == "human_confirmed"
    assert [row["provenance"] for row in truth["seeded_bugs"]] == [
        "human_independent", "human_independent", "human_prompted"]


@pytest.mark.parametrize("ordering", ["unknown", "independent_parallel", "human_read_ai_first",
                                     "ai_read_human_first"])
def test_ordering_roundtrip_preserves_exact_closed_vocabulary(ordering):
    trial = _trial(_live_corpus(), ordering=ordering)
    restored = BenchTrial.model_validate_json(trial.model_dump_json())
    assert restored.ordering == ordering
    assert restored.kind == "human_live"


def test_fixture_seeded_truth_and_oracle_kind_survive_json_roundtrip() -> None:
    corpus = _corpus()
    trial = bench.oracle_human_trial("oracle", corpus)
    restored = BenchCorpus.model_validate_json(corpus.model_dump_json())
    assert restored.mode == "fixture"
    assert restored.seeded_bugs[0].provenance == "fixture_seeded"
    assert BenchTrial.model_validate_json(trial.model_dump_json()).kind == "human_oracle"


def test_scorecard_delegates_exact_score_and_metadata_without_parallel_math(monkeypatch):
    corpus = _live_corpus()
    trials = [_trial(corpus, id="first", participant_label="first"),
              _trial(corpus, id="second", participant_label="second")]
    calls = []
    sentinels = {trial.id: {"probe": trial.id, "duration_s": None} for trial in trials}

    def independent_score(self, received):
        assert received is corpus
        calls.append(self.id)
        return sentinels[self.id]

    monkeypatch.setattr(BenchTrial, "score", independent_score)
    card = bench.scorecard(corpus, trials)
    assert calls == ["first", "second"]
    assert card == {"first": sentinels["first"], "second": sentinels["second"]}


@pytest.mark.parametrize("duration", [-1.0, float("nan"), float("inf"), -float("inf")])
def test_invalid_duration_is_refused_as_duration_validation(duration):
    with pytest.raises(ValueError, match="duration_s"):
        _trial(_live_corpus(), duration_s=duration)


@pytest.mark.parametrize("kind,participant", [("human_live", Participant.AUTOTESTER),
                                             ("human_oracle", Participant.AUTOTESTER),
                                             ("autotester", Participant.HUMAN)])
def test_kind_participant_mismatch_is_refused(kind, participant):
    with pytest.raises(ValueError, match=r"kind|participant"):
        _trial(_live_corpus(), kind=kind, participant=participant)


def test_mismatched_corpus_id_is_refused_instead_of_scored() -> None:
    corpus = _live_corpus()
    trial = _trial(corpus, corpus_id="different")
    with pytest.raises(ValueError, match="corpus"):
        trial.score(corpus)


def test_duplicate_truth_ids_are_refused_instead_of_double_weighted() -> None:
    payload = _live_corpus().model_dump()
    payload["seeded_bugs"].append(payload["seeded_bugs"][0])
    with pytest.raises(ValueError, match=r"duplicate|unique"):
        BenchCorpus.model_validate(payload)


def test_fixture_mode_cannot_claim_human_confirmed_truth() -> None:
    payload = _live_corpus().model_dump()
    payload["mode"] = "fixture"
    with pytest.raises(ValueError, match=r"fixture|provenance"):
        BenchCorpus.model_validate(payload)


def test_scorecard_calls_bench_trial_score_for_every_trial() -> None:
    corpus = _corpus()
    ai = bench.run_autotester_trial(
        "trial_ai", corpus, [_verdict("case_login", Result.FAIL)],
        {"case_login": "bug_login"}, duration_s=12.0,
    )
    human = bench.oracle_human_trial("trial_human", corpus)
    card = bench.scorecard(corpus, [ai, human])
    assert card["autotester-real-run"] == ai.score(corpus)
    assert card["human-oracle-baseline"] == human.score(corpus)


def test_untimed_timed_and_mixed_trials_score_time_axis_independently() -> None:
    """AT-655: untimed is unavailable (never 0 s); timed is verbatim; recall still computes."""
    corpus = _live_corpus()
    untimed = _trial(corpus).score(corpus)
    timed = _trial(corpus, duration_s=42.5).score(corpus)
    assert untimed["duration_s"] is None
    assert untimed["duration_s_unavailable_reason"] == "timing not recorded"
    assert timed["duration_s"] == 42.5
    assert timed["duration_s_unavailable_reason"] is None
    # Time availability must not leak into the other axes.
    for key in ("detection_rate", "severity_weighted_recall", "false_positive_rate"):
        assert untimed[key] == timed[key]


def test_stored_trial_without_duration_key_loads_as_untimed() -> None:
    """A legacy file with no duration_s key is untimed; an explicit 0.0 stays a measurement."""
    corpus = _live_corpus()
    raw = json.loads(_trial(corpus).model_dump_json())
    raw.pop("duration_s", None)
    legacy = type(_trial(corpus)).model_validate(raw)
    assert legacy.duration_s is None
    assert legacy.score(corpus)["duration_s"] is None
