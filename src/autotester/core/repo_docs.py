"""Repo-level documents: the living map, the ledger, the history, the router.

One job: name where the repo's own documents live (`docs/`, `CLAUDE.md`, `.goal/goal.json`)
and where its code-owned prompts and skills ship. Split out of `core/paths.py` (T-205/TF7) so
that file has room for the data-root helpers; `core.paths.RepoDocs` still resolves, so no
importer changed.
"""

from __future__ import annotations

from pathlib import Path


class RepoDocs:
    """Repo-level documents: the living map, the ledger, the history, the router."""

    def __init__(self, root: Path | None = None, *, prompts_dir: Path | None = None,
                 skills_dir: Path | None = None) -> None:
        from autotester.core.paths import repo_root  # lazy: paths re-exports this module

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
        """Prompts ship WITH THE CODE, so the DATA root (`AUTOTESTER_ROOT`) must not move
        them (AT-132). An EXPLICIT `root` still wins; pass `prompts_dir=` to substitute a
        stub tree by name (AT-137)."""
        if self._prompts_dir_override is not None:
            return self._prompts_dir_override
        if self._root_given:
            return self.root / "src" / "autotester" / "prompts"
        return Path(__file__).resolve().parents[1] / "prompts"

    @property
    def skills_dir(self) -> Path:
        """Migrated-prompt `SKILL.md` folders (T-175/D-041); code-owned like `prompts_dir`."""
        if self._skills_dir_override is not None:
            return self._skills_dir_override
        if self._root_given:
            return self.root / "src" / "autotester" / "skills"
        return Path(__file__).resolve().parents[1] / "skills"
