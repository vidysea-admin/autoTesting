"""AT-233: a near-miss must not read like "nothing was near" — T-136.

Split out of `test_score.py` when adding these pushed it past the 300-line
cap (`autotester doctor`, file-too-long). One responsibility: the rejected-
best-candidate branch of `stages/score.py::score`.

Contract: qa/contracts/video-learning.md (T-136 acceptance).
"""

from __future__ import annotations

from autotester.schema.enums import IssueCategory, Severity
from autotester.schema.issue import Issue
from autotester.stages.score import TruthRow, score

CLIP = "erp1.mp4 (Divya Kamboj, trainer pipeline)"


def a_row(**kw) -> TruthRow:
    return TruthRow(
        id=kw.pop("id", "E-01"),
        title=kw.pop("title", "Trainer cannot be moved past Shortlisted"),
        what_is_wrong=kw.pop("what_is_wrong", "Move reports Saving then silently reverts"),
        recording=kw.pop("recording", "erp1.mp4"),
        at_s=kw.pop("at_s", 29.0),
        row_number=kw.pop("row_number", 2),
    )


def an_issue(**kw) -> Issue:
    return Issue(
        project="erp",
        source_id=kw.pop("source_id", "src_1"),
        recording_label=kw.pop("recording_label", CLIP),
        at_s=kw.pop("at_s", 30.0),
        screen=kw.pop("screen", "Trainers"),
        title=kw.pop("title", "Trainer cannot be moved past Shortlisted"),
        what_is_wrong=kw.pop("what_is_wrong", "the Move button reverts with no message"),
        severity=kw.pop("severity", Severity.S1),
        category=kw.pop("category", IssueCategory.FEATURE_GAP),
        **kw)


def test_a_rejected_best_candidate_keeps_its_similarity_and_seconds_apart() -> None:
    """AT-233. A candidate that shares the recording and sits inside `window_s`
    but scores under `threshold` was discarded down to the same
    similarity=0.0/seconds_apart=None as a row with no candidate at all -- a
    reader tuning --threshold could not tell a near-miss from silence."""
    row = a_row(title="", what_is_wrong=(
        "Trainer stage kanban card ignores manual reorder inside Shortlisted column"))
    issue = an_issue(title="", what_is_wrong=(
        "Kanban card in Shortlisted column snaps back after a manual reorder"),
        at_s=31.0)

    card = score([row], [issue], threshold=0.99)  # real overlap, but forced below threshold

    match = card.matches[0]
    assert match.found is False
    assert match.similarity > 0.0, "the rejected candidate's score was discarded"
    assert match.seconds_apart is not None, "the rejected candidate's time gap was discarded"


def test_no_candidate_at_all_still_reads_as_zero_and_none() -> None:
    """The other half: when nothing shares the recording/window, there is truly
    nothing to report -- this must stay distinguishable from a near-miss."""
    row = a_row(recording="erp2.mp4")
    issue = an_issue()  # recording erp1.mp4 -- does not share row's recording

    card = score([row], [issue])

    match = card.matches[0]
    assert match.found is False
    assert match.similarity == 0.0
    assert match.seconds_apart is None


def test_the_near_miss_score_reaches_per_row_json() -> None:
    """The report is what a reader actually looks at when tuning --threshold;
    the Match field alone is not enough if as_dict() still flattens it away."""
    row = a_row(title="", what_is_wrong=(
        "Trainer stage kanban card ignores manual reorder inside Shortlisted column"))
    issue = an_issue(title="", what_is_wrong=(
        "Kanban card in Shortlisted column snaps back after a manual reorder"),
        at_s=31.0)

    report = score([row], [issue], threshold=0.99).as_dict()

    per_row = report["per_row"][0]
    assert per_row["found"] is False
    assert per_row["similarity"] > 0.0
    assert per_row["seconds_apart"] is not None
