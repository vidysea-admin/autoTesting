"""T-136 grade-fix G1/G2: what masked or withheld screenshots may do to a verdict.

G1: a judge FAIL that cites a screenshot the judge never received (withheld or absent), or whose
only basis is a visual the judge never saw, becomes INCONCLUSIVE (fail closed, mirrors the PASS
rule). G2: masking text bands alone no longer downgrades a PASS; a PASS stands when every image
was delivered AND deterministic DOM/network assertions were met. Contracts: grade.md,
browser-and-secrets.md B11, core-invariants C12. Offline, fake OCR, fake judge.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from autotester.core import image_privacy
from autotester.core.image_privacy import ImagePrivacyError
from autotester.providers.mock import MockProvider
from autotester.schema.enums import EvidenceKind, Outcome, Result
from autotester.schema.run import Evidence, RawResult
from autotester.schema.verdict import Criterion, Failure, Judgment, Rubric
from autotester.stages.grade import grade

HEADER = ("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\t"
          "left\ttop\twidth\theight\tconf\ttext\n")
WORDS = "5\t1\t1\t1\t1\t1\t10\t10\t20\t10\t99\tprivate\n"
BLANK = (0, 0, 255)  # a pixel colour the fake OCR treats as "no recognized text" (withheld)


def _shot(path: Path, *, blank: bool = False) -> None:
    Image.new("RGB", (100, 60), BLANK if blank else "white").save(path)


def _fake_ocr(monkeypatch) -> None:
    def ocr(path: Path) -> str:
        with Image.open(path) as image:
            if image.getpixel((0, 0)) == BLANK:
                raise ImagePrivacyError("no_recognized_text")
        return HEADER + WORDS
    monkeypatch.setattr(image_privacy, "_local_ocr", ocr)


def _rubric(required: bool = True) -> Rubric:
    return Rubric(id="rub_t", criteria=[Criterion(
        id="c1", text="Login leaves the sign-in page", evidence_required=required)])


def _result(*extra: str, shots: tuple[str, ...] = ("01-a.png", "02-b.png")) -> RawResult:
    evidence = [Evidence(kind=EvidenceKind.SCREENSHOT, path=p, step_order=i + 1)
                for i, p in enumerate(shots)]
    evidence += [Evidence(kind=EvidenceKind.DOM, path=text, step_order=2) for text in extra]
    return RawResult(case_id="case_t", outcome=Outcome.COMPLETED, evidence=evidence)


def _fail(*refs: str) -> Judgment:
    return Judgment(result=Result.FAIL, scoreboard="0/1", criteria_met=0, criteria_total=1,
                    failures=[Failure(criterion_id="c1", reason="still on sign-in",
                                      evidence_refs=list(refs))], defect_observed=True)


def _pass() -> Judgment:
    return Judgment(result=Result.PASS, scoreboard="1/1", criteria_met=1, criteria_total=1,
                    note="Landed on the dashboard.", defect_observed=False)


def _grade(tmp_path: Path, monkeypatch, judgment: Judgment, result: RawResult, *,
           blank: tuple[str, ...] = (), absent: tuple[str, ...] = (), required: bool = True):
    _fake_ocr(monkeypatch)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    for ev in result.evidence:
        if ev.kind is EvidenceKind.SCREENSHOT and ev.path not in absent:
            _shot(run_dir / ev.path, blank=ev.path in blank)
    judge = MockProvider(responses={"judge": [judgment]})
    return grade(_rubric(required), result, "run_1", judge, run_dir=run_dir)


# -- G1 ---------------------------------------------------------------------------------------

def test_g1_fail_citing_a_withheld_screenshot_is_inconclusive(tmp_path, monkeypatch) -> None:
    verdict = _grade(tmp_path, monkeypatch, _fail("case_t/02-b.png"),
                     _result(shots=("01-a.png", "02-b.png")), blank=("02-b.png",))
    assert verdict.result is Result.INCONCLUSIVE
    assert (verdict.images_requested, verdict.images_seen) == (2, 1)
    assert "02-b.png" in (verdict.note or "")


def test_g1_fail_citing_an_absent_screenshot_is_inconclusive(tmp_path, monkeypatch) -> None:
    verdict = _grade(tmp_path, monkeypatch, _fail("02-b.png"), _result(), absent=("02-b.png",))
    assert verdict.result is Result.INCONCLUSIVE


def test_g1_fail_citing_only_a_delivered_screenshot_stands(tmp_path, monkeypatch) -> None:
    verdict = _grade(tmp_path, monkeypatch, _fail("01-a.png"), _result(), blank=("02-b.png",))
    assert verdict.result is Result.FAIL
    assert verdict.failures, "the cited failure is kept"


def test_g1_fail_citing_a_dom_row_stands_even_with_a_withheld_screenshot(
    tmp_path, monkeypatch,
) -> None:
    row = "assert url: unmet (expected to contain '/dashboard')"
    verdict = _grade(tmp_path, monkeypatch, _fail(row), _result(row), blank=("02-b.png",))
    assert verdict.result is Result.FAIL


def test_g1_fail_with_no_refs_and_no_image_delivered_is_inconclusive(
    tmp_path, monkeypatch,
) -> None:
    verdict = _grade(tmp_path, monkeypatch, _fail(), _result(), blank=("01-a.png", "02-b.png"),
                     required=False)
    assert verdict.result is Result.INCONCLUSIVE


def test_g1_fail_with_no_refs_but_images_delivered_stands(tmp_path, monkeypatch) -> None:
    verdict = _grade(tmp_path, monkeypatch, _fail(), _result(), required=False)
    assert verdict.result is Result.FAIL


def test_g1_text_only_fail_with_no_screenshots_requested_is_untouched() -> None:
    judge = MockProvider(responses={"judge": [_fail("x")]})
    verdict = grade(_rubric(), RawResult(case_id="c", outcome=Outcome.COMPLETED, evidence=[]),
                    "run_1", judge)
    assert verdict.result is Result.FAIL  # no screenshots requested: nothing was withheld


# -- G2 ---------------------------------------------------------------------------------------

MET = "assert url: met (expected to contain '/dashboard')"


def test_g2_pass_stands_when_all_images_delivered_and_an_assertion_was_met(
    tmp_path, monkeypatch,
) -> None:
    verdict = _grade(tmp_path, monkeypatch, _pass(), _result(MET))
    assert verdict.result is Result.PASS
    assert (verdict.images_requested, verdict.images_seen) == (2, 2)
    assert "Visual evidence incomplete" in (verdict.note or ""), "B11: coverage stays disclosed"


def test_g2_pass_without_any_met_assertion_stays_held(tmp_path, monkeypatch) -> None:
    """Asserted text not determinable from deterministic evidence: keep the downgrade."""
    verdict = _grade(tmp_path, monkeypatch, _pass(), _result())
    assert verdict.result is Result.INCONCLUSIVE


def test_g2_pass_is_held_when_a_screenshot_was_withheld(tmp_path, monkeypatch) -> None:
    verdict = _grade(tmp_path, monkeypatch, _pass(), _result(MET), blank=("02-b.png",))
    assert verdict.result is Result.INCONCLUSIVE
    assert "graded on 1 of 2 screenshots" in (verdict.note or "")


def test_g2_pass_is_held_when_a_screenshot_is_absent(tmp_path, monkeypatch) -> None:
    verdict = _grade(tmp_path, monkeypatch, _pass(), _result(MET), absent=("02-b.png",))
    assert verdict.result is Result.INCONCLUSIVE


def test_g2_unmet_assertion_still_blocks_pass(tmp_path, monkeypatch) -> None:
    result = _result(MET, "assert visible_text: unmet (expected to contain 'Welcome')")
    assert _grade(tmp_path, monkeypatch, _pass(), result).result is Result.INCONCLUSIVE


def test_g2_pass_with_note_describing_a_defect_is_still_held(tmp_path, monkeypatch) -> None:
    bad = _pass().model_copy(update={"note": "Page crashed after login.", "defect_observed": None})
    assert _grade(tmp_path, monkeypatch, bad, _result(MET)).result is Result.INCONCLUSIVE


def test_g2_pass_is_held_when_a_dashboard_screenshot_is_withheld_for_mask_size(
    tmp_path, monkeypatch,
) -> None:
    """T-136 gate A: raising the masking limit keeps a dense dashboard, but a screenshot that is
    still withheld for `mask_exceeds_limit` (all text) never lets a met assertion make it a PASS."""
    rows = "".join(f"5\t1\t1\t1\t{n}\t1\t5\t{n*20-20}\t90\t20\t99\tword{n}\n" for n in (1, 2, 3))
    verdict = _grade(tmp_path, monkeypatch, _pass(), _result(MET))  # installs the fake OCR
    assert verdict.result is Result.PASS and verdict.images_seen == 2
    monkeypatch.setattr(image_privacy, "_local_ocr", lambda _: HEADER + rows)  # 100% text bands
    held = grade(_rubric(), _result(MET), "run_2", MockProvider(responses={"judge": [_pass()]}),
                 run_dir=tmp_path / "run")
    assert held.result is Result.INCONCLUSIVE
    assert (held.images_requested, held.images_seen) == (2, 0)
    assert "withheld or absent" in (held.note or "")
