"""TA16: automatic item-to-oracle matching, the human override, and the 13-row oracle check."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from autotester.schema.bench import BenchCorpus, SeededBug
from autotester.schema.enums import Severity
from autotester.schema.review_recall import ReviewRecall
from autotester.schema.video_review import ConfirmItem, VideoReview

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "review_recall.py"
ROWS = {
    1: ("School Journey Communication history", "emails listed with raw placeholder student name"),
    2: ("Payments checkout", "duplicate charge shown twice after retry"),
}


def _cli():
    spec = importlib.util.spec_from_file_location("review_recall", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _item(i: str, screen: str, seen: str) -> ConfirmItem:
    return ConfirmItem(id=i, time_s=1, screen=screen, seen=seen, suggestion="fix it",
                       severity=Severity.S1, source_id="src_a", origin="visual")


def _args(tmp_path: Path, expected: str = "2") -> list[str]:
    bugs = [SeededBug(id=f"B{n}", description=d, severity=Severity.S1, location=loc,
                      detect_hint=d, provenance="ai_video_review") for n, (loc, d) in ROWS.items()]
    corpus = BenchCorpus(id="oc", app="a", build_ref="b", seeded_bugs=bugs,
                         mode="known_bugs_ai_assisted")
    review = VideoReview(id="rv1", source_id="src_a", status="ok", summary="flow", items=[
        _item("i1", "School Journey Communication history",
              "past emails listed with raw placeholder student name"),
        _item("i2", "Login", "button colour slightly off")])
    (tmp_path / "r.json").write_text(review.model_dump_json())
    (tmp_path / "o.json").write_text(corpus.model_dump_json())
    return ["--review", str(tmp_path / "r.json"), "--oracle", str(tmp_path / "o.json"),
            "--out", str(tmp_path / "out" / "recall.json"), "--expected-n", expected]


def _load(tmp_path: Path) -> ReviewRecall:
    return ReviewRecall.model_validate_json((tmp_path / "out" / "recall.json").read_text())


def test_automatic_matching_needs_no_matches_file(tmp_path):
    assert _cli().main(_args(tmp_path)) == 0
    rec = _load(tmp_path)
    assert rec.found_ids == ["B1"] and rec.missed_ids == ["B2"]
    assert rec.unconfirmed_ids == ["i2"] and rec.match_method == "automatic lexical"


def test_override_replaces_automatic(tmp_path):
    (tmp_path / "m.json").write_text(json.dumps({"B2": ["i2"]}))
    assert _cli().main([*_args(tmp_path), "--matches", str(tmp_path / "m.json")]) == 0
    rec = _load(tmp_path)
    assert rec.found_ids == ["B2"] and rec.match_method == "human override"


def test_oracle_must_have_expected_high_rows(tmp_path):
    assert _cli().main(_args(tmp_path, expected="13")) == 2
    assert not (tmp_path / "out").exists()
