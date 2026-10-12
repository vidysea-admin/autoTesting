"""TF7 (team-foundation.md): `safe_name` refuses the whole Windows device/stream/reserved class.

Table-driven over the class, not examples: every reserved device name (with and without an
extension, any case, with trailing spaces), the console handles `CONIN$`/`CONOUT$`, any `:`
(drive letter, `nul:`, NTFS alternate data stream `ab:stream`) and each of `< > " | ? *`.
"""

from __future__ import annotations

from itertools import product
from pathlib import Path

import pytest

from autotester.core import paths, safe_names
from autotester.core.safe_names import UnsafeName
from autotester.store import team_store

DEVICES = ["con", "prn", "aux", "nul", "conin$", "conout$",
           *(f"com{n}" for n in (*range(1, 10), "\u00b9", "\u00b2", "\u00b3")),
           *(f"lpt{n}" for n in (*range(1, 10), "\u00b9", "\u00b2", "\u00b3"))]
FORBIDDEN_CHARS = ["<", ">", ":", '"', "|", "?", "*"]


def _device_forms() -> list[str]:
    forms = []
    for dev, (case, suffix) in product(DEVICES, product((str.lower, str.upper, str.title),
                                                       ("", ".txt", ".tar.gz", " ", " .log"))):
        forms.append(case(dev) + suffix)
    return forms


def _char_forms() -> list[str]:
    shapes = ("{c}", "a{c}", "{c}a", "a{c}b", "nul{c}", "ab{c}stream")
    return [shape.format(c=c) for c, shape in product(FORBIDDEN_CHARS, shapes)]


@pytest.mark.parametrize("name", _device_forms())
def test_every_reserved_device_form_is_refused(name: str) -> None:
    with pytest.raises(UnsafeName):
        safe_names.safe_name(name)


@pytest.mark.parametrize("name", _char_forms())
def test_every_forbidden_character_form_is_refused(name: str) -> None:
    with pytest.raises(UnsafeName):
        safe_names.safe_name(name)


@pytest.mark.parametrize("name", ["nul:", "ab:stream", "CONIN$", "CONOUT$", "a<b", 'a"b', "a|b",
                                  "a?b", "a*b", "a>b"])
def test_the_named_cases_are_refused_before_any_directory_exists(name: str, tmp_path: Path) -> None:
    root = tmp_path / "root"
    with pytest.raises(UnsafeName):
        paths.team_path(name, root=root)
    with pytest.raises(UnsafeName):
        team_store.create_marker(root, name, "m")
    assert not root.exists()


@pytest.mark.parametrize("name", [
    "demo", "a-b", "run-01", "x.y", "report_v1.json", "conn", "nulled", "console", "com10", "lpt0",
    "a$b", "coninx", "con-1"])
def test_ordinary_names_still_pass(name: str) -> None:
    assert safe_names.safe_name(name) == name


@pytest.mark.parametrize("key", ["nul:fixed:x", "ab:stream", "CONIN$", "a<b>c|d?e*f\"g"])
def test_slot_keys_with_these_characters_encode_to_a_safe_name(key: str) -> None:
    name = safe_names.encode_slot_key(key)
    assert not set(FORBIDDEN_CHARS) & set(name)
    assert safe_names.safe_name(name) == name
