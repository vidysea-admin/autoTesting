"""TA16 producer: fixture reviews + fixture oracle -> recall.json. No model, no browser."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from autotester.schema.bench import BenchCorpus, SeededBug
from autotester.schema.enums import Severity
from autotester.schema.review_recall import ReviewRecall
from autotester.schema.video_review import ConfirmItem, VideoReview

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "review_recall.py"


def _cli():
    spec = importlib.util.spec_from_file_location("review_recall", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _item(i: str) -> ConfirmItem:
    return ConfirmItem(id=i, time_s=1, screen="s", seen="x", suggestion="y",
                       severity=Severity.S1, source_id="src_a", origin="visual")


def _files(tmp_path: Path, matches: dict) -> list[str]:
    review = VideoReview(id="rv1", source_id="src_a", status="ok", summary="flow",
                         items=[_item("i1"), _item("i2"), _item("i3")], duration_s=10,
                         not_reviewed=[(2.0, 4.0)], calls=3, cost_usd=0.1)
    bugs = [SeededBug(id=f"B{n}", description="d", severity=sev, location="l", detect_hint="h",
                      provenance="ai_video_review")
            for n, sev in [(1, Severity.S1), (2, Severity.S1), (3, Severity.S1), (4, Severity.S2)]]
    corpus = BenchCorpus(id="oc", app="a", build_ref="b", seeded_bugs=bugs,
                         mode="known_bugs_ai_assisted")
    (tmp_path / "r.json").write_text(review.model_dump_json())
    (tmp_path / "o.json").write_text(corpus.model_dump_json())
    (tmp_path / "m.json").write_text(json.dumps(matches))
    return ["--review", str(tmp_path / "r.json"), "--oracle", str(tmp_path / "o.json"),
            "--matches", str(tmp_path / "m.json"), "--out", str(tmp_path / "out" / "recall.json")]


def test_recall_k_missed_unconfirmed_and_label(tmp_path):
    args = _files(tmp_path, {"B1": ["i1"], "B4": ["i2"]})
    assert _cli().main([*args, "--elapsed-s", "12.5"]) == 0
    rec = ReviewRecall.model_validate_json((tmp_path / "out" / "recall.json").read_text())
    assert (rec.k, rec.n) == (1, 3) and rec.found_ids == ["B1"]
    assert rec.missed_ids == ["B2", "B3"]
    assert rec.unconfirmed_ids == ["i3"] and rec.unconfirmed_count == 1
    assert rec.oracle.recall_basis == "AI-assisted video review, not independent"
    assert rec.independent is False and rec.claim == "measured on 1 videos"
    assert rec.not_reviewed["src_a"] == [(2.0, 4.0)] and rec.time_to_review_s == 12.5


def test_unknown_ids_refuse_without_writing(tmp_path):
    args = _files(tmp_path, {"B1": ["nope"]})
    assert _cli().main(args) == 2
    assert not (tmp_path / "out").exists()


def test_no_matches_is_zero_recall_not_error(tmp_path):
    assert _cli().main(_files(tmp_path, {})) == 0
    rec = ReviewRecall.model_validate_json((tmp_path / "out" / "recall.json").read_text())
    assert rec.k == 0 and rec.recall == 0 and rec.unconfirmed_count == 3
