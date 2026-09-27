"""The cache — VL2/VL2b/VL3. The only part of Track A that spends money.

Every provider here is a spy and every assertion is on the NUMBER OF CALLS,
because "the cache works" is a claim about calls, not about output. Split from
`test_analyze_video.py` at the 300-line cap; that file keeps the behaviour of
the driver itself (narration slicing, refusals, persistence).

Contract: qa/contracts/video-learning.md VL2/VL2b/VL3.
"""

from __future__ import annotations

from video_fakes import SpyProvider, prepared

from autotester.core.paths import RepoDocs
from autotester.stages.analyze_video import PROMPT_NAMES, SKILL_NAMES, analyze

__all__ = ["prepared"]


# -- the rule that costs money if it is wrong ------------------------------

def test_every_model_sees_every_prompt_on_every_chunk(prepared) -> None:
    store, source = prepared
    pro, flash = SpyProvider("spy:pro"), SpyProvider("spy:flash")

    analyze(store, source, [pro, flash], docs=RepoDocs())

    assert len(pro.calls) == len(PROMPT_NAMES) * 2   # 2 prompts x 2 chunks
    assert len(flash.calls) == len(PROMPT_NAMES) * 2


def test_a_second_analyze_makes_zero_provider_calls(prepared) -> None:
    """The rule this whole stage is shaped by. A re-run after a crash, after a
    code change, or just to look again must cost nothing."""
    store, source = prepared
    pro = SpyProvider("spy:pro")

    analyze(store, source, [pro], docs=RepoDocs())
    first = len(pro.calls)
    pro.calls.clear()

    analyze(store, source, [pro], docs=RepoDocs())

    assert first > 0
    assert pro.calls == [], "a cached observation was re-requested"


def test_force_is_the_only_way_past_the_cache(prepared) -> None:
    store, source = prepared
    pro = SpyProvider("spy:pro")
    analyze(store, source, [pro], docs=RepoDocs())
    pro.calls.clear()

    analyze(store, source, [pro], docs=RepoDocs(), force=True)

    assert len(pro.calls) == len(PROMPT_NAMES) * 2


def test_adding_a_second_model_only_calls_the_new_one(prepared) -> None:
    """The cache is keyed per model, so widening the ensemble costs only the
    widening — otherwise nobody would ever add the second model."""
    store, source = prepared
    pro, flash = SpyProvider("spy:pro"), SpyProvider("spy:flash")
    analyze(store, source, [pro], docs=RepoDocs())
    pro.calls.clear()

    analyze(store, source, [pro, flash], docs=RepoDocs())

    assert pro.calls == []
    assert len(flash.calls) == len(PROMPT_NAMES) * 2


def test_a_half_written_observation_heals_instead_of_blocking(prepared) -> None:
    """VL2b. The cache exists to survive a crash, and a crash is exactly what
    leaves a truncated JSON file behind.

    AT-199/AT-200: reading came before the force test, so a corrupt file raised
    out of `analyze` AND `--force` could not clear it — the one situation the
    cache promises to handle was the one it made unrecoverable, with no way out
    but deleting files by hand."""
    store, source = prepared
    pro = SpyProvider("spy:pro")
    analyze(store, source, [pro], docs=RepoDocs())
    corrupt = sorted(store.paths.source_observations_dir(source.id).glob("*.json"))[0]
    corrupt.write_text('{"source_id": "src_1", "provider', encoding="utf-8")
    pro.calls.clear()

    analysis = analyze(store, source, [pro], docs=RepoDocs())

    assert len(pro.calls) == 1, "the damaged chunk was not re-requested"
    assert analysis.observations_used == len(PROMPT_NAMES) * 2


def _write_skill(skills_dir, skill_name: str, body: str) -> None:
    """A minimal but valid `SKILL.md` (T-175 Agent Skills shape) for a stub tree."""
    folder = skills_dir / skill_name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SKILL.md").write_text(
        f"---\nname: {skill_name}\ndescription: stub for a cache-invalidation test\n---\n\n{body}",
        encoding="utf-8",
    )


def test_editing_a_prompt_invalidates_its_cached_answers(prepared, tmp_path) -> None:
    """AT-200. The cache was keyed on the prompt's NAME, and editing a prompt
    file does not change its name — so a changed question silently returned the
    answer to the old one. That failure is invisible in the artifact, which is
    what makes it the kind that gets a cache switched off entirely.

    T-175: prompts ship as `SKILL.md` folders now, read through `skills_dir`
    instead of `prompts_dir` — the override moves with them."""
    store, source = prepared
    skills = tmp_path / "skills"
    for name in PROMPT_NAMES:
        _write_skill(skills, SKILL_NAMES[name], "ask this. {{NARRATION}} {{SOURCE_LABEL}}")

    class EditableSkills(RepoDocs):
        """Skills ship with the CODE (`skills_dir` deliberately ignores the
        data root), so editing one for a test means overriding that property
        rather than pointing `AUTOTESTER_ROOT` somewhere."""

        @property
        def skills_dir(self):
            return skills

    docs = EditableSkills()
    pro = SpyProvider("spy:pro")
    analyze(store, source, [pro], docs=docs)
    pro.calls.clear()

    _write_skill(skills, SKILL_NAMES[PROMPT_NAMES[0]],
                 "ask something ELSE. {{NARRATION}} {{SOURCE_LABEL}}")
    analyze(store, source, [pro], docs=docs)

    assert len(pro.calls) == 2, "the edited prompt reused the old answer"
    assert all("ELSE" in prompt for _, prompt in pro.calls)


def test_the_analysis_records_how_many_calls_it_is_missing(prepared) -> None:
    """VL3/AT-198: a reading built from 1 of 4 answers must not look like one
    built from 4 of 4 — they carry the same screens and the same issues."""
    store, source = prepared
    working, broken = SpyProvider("spy:pro"), SpyProvider("spy:broken", fail=True)

    analysis = analyze(store, source, [working, broken], docs=RepoDocs())

    assert analysis.observations_expected == 2 * len(PROMPT_NAMES) * 2
    assert analysis.observations_used == len(PROMPT_NAMES) * 2
    assert not analysis.is_complete
