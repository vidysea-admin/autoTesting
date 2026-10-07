"""RECONCILE stage. Contract: qa/contracts/reconcile.md RC3-RC13 (RC1/2/8 in test_reconcile_schema).

Offline and unpaid (RC13): MockProvider judge, the frozen fixture, no network.
"""

from __future__ import annotations

import re
import socket
from pathlib import Path

import pytest
from reconcile_fakes import dumped, flow, frozen, judge_mock, judge_prompts, node, screen, video

from autotester.providers.base import Unsupported
from autotester.providers.mock import MockProvider
from autotester.schema.media import Transcript, TranscriptSegment
from autotester.stages import reconcile as rc
from autotester.stages.reconcile import band, combined_score, reconcile
from autotester.stages.screen_identity import dangling_references

MODULE = Path(rc.__file__)
SECRET = "Zq7-hunter-Secret-991"


def test_rc3_narration_not_in_transcript_is_rejected_and_the_step_kept() -> None:
    spec = video("src_a", [screen("scr_1", "Home", "/home")],
                 [flow("Go", "src_a", ["scr_1"], narration="words nobody said")])
    said = {"src_a": Transcript(source_id="src_a", segments=[
        TranscriptSegment(start=0, end=2, text="Something  ELSE entirely")])}
    out, report = reconcile([spec], [], transcripts=said)
    assert out.flows[0].steps[0].narration is None and len(out.flows[0].steps) == 1
    assert [(r.flow_id, r.order) for r in report.narration_unverified] == [(out.flows[0].id, 1)]
    kept, _ = reconcile([video("src_a", spec.screens, [flow("Go", "src_a", ["scr_1"],
                         narration="something else")])], [], transcripts=said)
    assert kept.flows[0].steps[0].narration == "something else"  # whitespace/case-normalised


def test_rc3_narration_is_scrubbed_before_it_is_stored() -> None:
    quote = f"my password is {SECRET} ok"
    spec = video("src_a", [screen("scr_1", "Home", "/home")],
                 [flow("Go", "src_a", ["scr_1"], narration=quote)])
    said = {"src_a": Transcript(source_id="src_a", segments=[
        TranscriptSegment(start=0, end=2, text=quote)])}
    out, report = reconcile([spec], [], transcripts=said, secrets={"PATHLYNKS_PW": SECRET})
    assert "[REDACTED]" in (out.flows[0].steps[0].narration or "")
    assert SECRET not in dumped(out, report).decode("utf-8")


def test_rc4_three_ids_for_one_route_fold_to_one_and_every_reference_follows() -> None:
    screens = [screen("scr_b", "Dash", "/dash", source="src_a", t=5), screen("scr_a", "Dashboard",
               "/dash/", source="src_a", t=1), screen("scr_c", "Home", "/dash?x=1", t=9)]
    spec = video("src_a", screens, [flow("Go", "src_a", ["scr_b", "scr_c", "scr_a"])])
    out, report = reconcile([spec], [])
    assert [s.id for s in out.screens] == ["scr_a"]
    assert report.folded == {"scr_b": "scr_a", "scr_c": "scr_a"}
    f = out.flows[0]
    assert {f.entry_screen, f.exit_screen, *(s.screen_id for s in f.steps)} == {"scr_a"}
    assert dangling_references(out) == []


def test_rc4_screens_without_a_route_are_never_folded_on_route_alone() -> None:
    spec = video("src_a", [screen("scr_1", "A"), screen("scr_2", "A")],
                 [flow("Go", "src_a", ["scr_1", "scr_2"])])
    out, report = reconcile([spec], [])
    assert len(out.screens) == 2 and report.folded == {}


@pytest.mark.parametrize(("signals", "total", "expected"), [
    ((1.0, 1.0, 0.2), 0.8, "matched"), ((1.0, 0.16, 1.0), 0.79, "ambiguous"),
    ((1.0, 0.0, 0.0), 0.5, "ambiguous"), ((0.0, 1.0, 0.96), 0.49, "new")])
def test_rc5_boundaries_land_in_the_fixed_bands(signals: tuple[float, float, float], total: float,
                                                 expected: str) -> None:
    assert combined_score(*signals) == total
    assert band(total) == expected


def test_rc5_thresholds_have_exactly_one_literal_each() -> None:
    source = MODULE.read_text(encoding="utf-8")
    assert len(re.findall(r"(?<![\d.])0\.8(?!\d)", source)) == 1
    assert len(re.findall(r"(?<![\d.])0\.5(?!\d)", source)) == 1


def test_rc5_every_row_records_three_signals_total_band_and_decider() -> None:
    videos, crawl, said = frozen()
    _, report = reconcile(videos, crawl, judge_mock(), transcripts=said)
    for row in report.matches:
        assert row.total == combined_score(row.route, row.title, row.elements)
        assert row.decided_by in ("rules", "judge")
        if row.decided_by == "rules":
            assert row.band == band(row.total)


def test_rc6_judge_is_called_once_per_ambiguous_row_and_never_for_rule_rows() -> None:
    videos, crawl, said = frozen()
    provider = judge_mock()
    _, report = reconcile(videos, crawl, provider, transcripts=said)
    ambiguous = [r for r in report.matches if rc.AMBIGUOUS_AT <= r.total < rc.MATCHED_AT]
    assert ambiguous, "the frozen sample must exercise the judge"
    assert len(judge_prompts(provider)) == len(ambiguous)


def _decoy() -> tuple[list, list]:
    spec = video("src_a", [screen("scr_1", "Billing ledger", "/app", ("Invoice table",))],
                 [flow("Pay", "src_a", ["scr_1"])])
    return [spec], [node("/app", "Team chat", [("button", "Send message")])]


@pytest.mark.parametrize(("provider", "note"), [
    (judge_mock(confidence=0.79), "low_confidence"), (MockProvider(), "judge_error"),
    (None, "no_judge")])
def test_rc6_decoy_low_confidence_and_errors_stay_ambiguous(provider: object, note: str) -> None:
    videos, crawl = _decoy()
    out, report = reconcile(videos, crawl, provider)  # type: ignore[arg-type]
    assert report.matches[0].band == "ambiguous" and report.matches[0].note == note
    assert out.screens[0].video_only is False


def test_rc6_unsupported_judge_stays_ambiguous_and_a_confident_judge_matches() -> None:
    class NoJudge(MockProvider):
        def judge(self, *a: object, **k: object) -> object:
            raise Unsupported("no judge role")
    videos, crawl = _decoy()
    assert reconcile(videos, crawl, NoJudge())[1].matches[0].band == "ambiguous"
    row = reconcile(videos, crawl, judge_mock(confidence=0.8))[1].matches[0]
    assert (row.band, row.decided_by) == ("matched", "judge")


def test_rc7_every_video_screen_lands_in_exactly_one_band_and_new_ones_survive() -> None:
    videos, crawl, said = frozen()
    out, report = reconcile(videos, crawl, judge_mock(), transcripts=said)
    video_ids = {s.id for s in out.screens}
    assert sorted(r.screen_id for r in report.matches) == sorted(video_ids)
    counts = {b: sum(r.band == b for r in report.matches) for b in ("matched", "ambiguous", "new")}
    assert sum(counts.values()) == len(video_ids) and counts["new"] > 20
    new = {r.screen_id for r in report.matches if r.band == "new"}
    assert new == {s.id for s in out.screens if s.video_only}
    assert dangling_references(out) == []


def test_rc11_same_inputs_give_byte_identical_output_in_any_input_order() -> None:
    videos, crawl, said = frozen()
    first = dumped(*reconcile(videos, crawl, judge_mock(), transcripts=said))
    swapped = [v.model_copy(update={"flows": list(reversed(v.flows))}) for v in reversed(videos)]
    assert dumped(*reconcile(swapped, list(reversed(crawl)), judge_mock(),
                             transcripts=said)) == first


def test_rc11_reconciling_its_own_output_changes_nothing_and_calls_no_judge() -> None:
    videos, crawl, said = frozen()
    rule_only = [v.model_copy(update={"screens": [s for s in v.screens if s.url_pattern not in (
        "/", "/signup")]}) for v in videos]  # the only routes the crawl shares: fully rule-decided
    out, report = reconcile(rule_only, crawl, judge_mock(), transcripts=said)
    again_provider = judge_mock()
    again, report2 = reconcile(rule_only, crawl, again_provider, existing=out, transcripts=said)
    assert again is out and dumped(again, report2) == dumped(out, report)
    assert judge_prompts(again_provider) == []


def test_rc12_no_raw_secret_reaches_the_judge_prompt() -> None:
    videos, crawl = _decoy()
    s = videos[0].screens[0].model_copy(update={"signals": [f"token {SECRET}"]})
    f = flow("Pay", "src_a", ["scr_1"], narration=f"say {SECRET}", value=SECRET)
    spec = video("src_a", [s], [f])
    said = {"src_a": Transcript(source_id="src_a", segments=[
        TranscriptSegment(start=0, end=1, text=f"say {SECRET}")])}
    provider = judge_mock()
    reconcile([spec], crawl, provider, transcripts=said, secrets={"PATHLYNKS_PW": SECRET})
    prompts = judge_prompts(provider)
    assert len(prompts) == 1 and SECRET not in prompts[0] and "[REDACTED]" in prompts[0]


def test_rc12_an_unscrubbable_spelling_refuses_the_call() -> None:
    videos, crawl = _decoy()
    s = videos[0].screens[0].model_copy(update={"signals": [SECRET[::-1]]})
    provider = judge_mock()
    _, report = reconcile([video("src_a", [s], videos[0].flows)], crawl, provider,
                          secrets={"PATHLYNKS_PW": SECRET})
    assert judge_prompts(provider) == [] and report.matches[0].note == "refused"


def test_rc12_module_uses_the_seam_and_a_prompt_file() -> None:
    source = MODULE.read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(anthropic|google|requests|httpx)", source, re.M)
    assert "load_skill_prompt(" in source and "assert_no_raw_secrets(" in source
    skill = MODULE.parents[1] / "skills" / rc.SKILL_NAME / "SKILL.md"
    assert skill.is_file()


def test_rc13_runs_with_sockets_blocked_and_no_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    def refuse(*_a: object, **_k: object) -> None:
        raise AssertionError("network attempted")
    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    videos, crawl, said = frozen()
    out, report = reconcile(videos, crawl, judge_mock(), transcripts=said)
    assert report.flows_out == len(out.flows)


def test_rc13_reconcile_tests_import_no_real_provider() -> None:
    here = Path(__file__).parent
    for name in ("test_reconcile.py", "test_reconcile_schema.py", "reconcile_fakes.py"):
        text = (here / name).read_text(encoding="utf-8")
        assert not re.search(r"providers\.(gemini|anthropic|langchain)", text), name
