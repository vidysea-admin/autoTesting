"""Prompt-as-SKILL.md migration (T-175). Contract: qa/contracts/skills.md SK1-SK4.

Covers the four prompts D-041 names for this unit -- grader, expand/test-design,
video-issues (bug-hunting), ingest -- now living as `SKILL.md` folders under
`skills_dir` (Agent Skills open standard: YAML frontmatter + body), read through
exactly one loader (`providers.base.load_skill_prompt`). `relitigation_v1.md`
and `agent_fix_v1.md` are out of scope (contract's explicit no-fire list) and
are asserted absent from this file's claims, never touched here.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from autotester.core.paths import RepoDocs
from autotester.core.redact import placeholder_keys
from autotester.providers.base import _FRONTMATTER_RE as FRONTMATTER_RE
from autotester.providers.base import load_skill_prompt

SKILL_NAMES = ["grade", "expand-case", "video-issues", "ingest-video"]
GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden_prompts"
GOLDEN_BY_SKILL = {
    "grade": "grade.md",
    "expand-case": "expand-case.md",
    "video-issues": "video-issues.md",
    "ingest-video": "ingest-video.md",
}
STAGE_FILES = [
    Path("src/autotester/stages/grade.py"),
    Path("src/autotester/stages/expand.py"),
    Path("src/autotester/stages/ingest.py"),
    Path("src/autotester/stages/analyze_video.py"),
]
REPO_ROOT = Path(__file__).resolve().parents[1]


# -- SK1: each migrated prompt is a valid Agent-Skills SKILL.md --------------

@pytest.mark.parametrize("skill", SKILL_NAMES)
def test_sk1_each_skill_is_a_valid_agent_skills_folder(skill: str) -> None:
    path = RepoDocs().skills_dir / skill / "SKILL.md"
    assert path.exists(), f"{path} missing"
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    assert match is not None, f"{skill}/SKILL.md has no leading '---'...'---' frontmatter block"
    meta = match.group("meta")
    name = re.search(r"^name:\s*(.+)$", meta, re.MULTILINE)
    desc = re.search(r"^description:\s*(.+)$", meta, re.MULTILINE)
    assert name and name.group(1).strip(), "frontmatter 'name' is missing/empty"
    assert desc and desc.group(1).strip(), "frontmatter 'description' is missing/empty"
    assert match.group("body").strip(), "SKILL.md body is empty"


# -- SK2: one loader, reached through the provider seam ----------------------

def test_sk2_no_stage_reads_a_migrated_prompt_by_itself() -> None:
    """`grep -rn` for an inline `read_text(...encoding...)` prompt read, over
    the four migrated stages only -- `agent_loop.py`/`relitigation.py` are out
    of scope (contract no-fire list) and legitimately keep their own
    `docs.prompts_dir` read for the two prompts this unit does not touch."""
    inline_read = re.compile(r"read_text\(.*encoding")
    for rel in STAGE_FILES:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert not inline_read.search(text), f"{rel} still reads a prompt file itself"
        assert "load_skill_prompt(" in text, f"{rel} does not call the loader"


def test_sk2_loader_is_defined_in_exactly_one_module() -> None:
    hits = [
        p for p in (REPO_ROOT / "src" / "autotester").rglob("*.py")
        if "def load_skill_prompt(" in p.read_text(encoding="utf-8")
    ]
    assert hits == [REPO_ROOT / "src" / "autotester" / "providers" / "base.py"]


def test_sk2_loader_raises_a_named_error_when_frontmatter_is_missing(tmp_path: Path) -> None:
    """The loader is the one place a malformed SKILL.md is caught -- a plain
    `.md` with no frontmatter must fail loudly, not silently degrade."""
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "SKILL.md").write_text("just a prompt, no frontmatter", encoding="utf-8")
    with pytest.raises(ValueError, match="frontmatter"):
        load_skill_prompt("broken", skills_dir=tmp_path)


# -- SK3: behaviour-preserving (byte-identical to the pre-migration file) ---

@pytest.mark.parametrize("skill", SKILL_NAMES)
def test_sk3_rendered_prompt_is_byte_identical_to_the_pre_migration_file(skill: str) -> None:
    """`tests/fixtures/golden_prompts/<skill>.md` was captured with
    `read_text()` -- the same universal-newline normalisation the old
    `(docs.prompts_dir / PROMPT_NAME).read_text(...)` call already applied --
    from the loose `prompts/*.md` file at the commit before T-175 moved it.
    An empty diff here is SK3's only pass shape for an undocumented change."""
    rendered = load_skill_prompt(skill)
    expected = (GOLDEN_DIR / GOLDEN_BY_SKILL[skill]).read_text(encoding="utf-8")
    assert rendered == expected


# -- SK4: credentials boundary is unchanged ----------------------------------

@pytest.mark.parametrize("skill", SKILL_NAMES)
def test_sk4_secret_placeholders_survive_unchanged(skill: str) -> None:
    """Whatever `{{SECRET:KEY}}` placeholders the OLD prompt carried (none, for
    three of the four; `expand-case` mentions the placeholder in its own
    instructions to the model) are exactly the same set after migration --
    substitution still only ever happens at `page.fill()` time, never here."""
    golden = (GOLDEN_DIR / GOLDEN_BY_SKILL[skill]).read_text(encoding="utf-8")
    rendered = load_skill_prompt(skill)
    assert placeholder_keys(rendered) == placeholder_keys(golden)


def test_sk4_no_migrated_skill_or_reference_carries_a_secret_value() -> None:
    """C5: a real credential VALUE must never reach a prompt file. `.env`'s own
    declared values (if the repo-root file exists here) are the concrete
    things this guards against; an empty/missing `.env` still leaves the
    placeholder-only shape asserted above."""
    env_path = REPO_ROOT / ".env"
    values = []
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                _, _, value = line.partition("=")
                value = value.strip()
                if value:
                    values.append(value)
    for skill in SKILL_NAMES:
        text = load_skill_prompt(skill)
        for value in values:
            assert value not in text, f"{skill}/SKILL.md carries a raw .env value"
