"""Drive link parsing (team-intake.md TI7, hosting.md HO32): only an id survives, only Google hosts.

Every case is a thing a person can paste into the Add-videos box: the five accepted shapes, and
the hostile ones HO32 lists by name. A refusal never echoes the pasted text (it may hold a token).
"""

from __future__ import annotations

import pytest

from autotester.sources.drive_link import DriveLinkError, parse_drive_link

FID = "1AbCdEfGhIjKlMnOpQrStUvWxYz_-0123"


@pytest.mark.parametrize("text, kind", [
    (f"https://drive.google.com/file/d/{FID}/view?usp=sharing", "file"),
    (f"https://drive.google.com/file/u/1/d/{FID}/view", "file"),
    (f"https://drive.google.com/open?id={FID}", "unknown"),
    (f"https://drive.google.com/uc?export=download&id={FID}", "unknown"),
    (f"https://drive.google.com/drive/folders/{FID}?usp=sharing", "folder"),
    (f"https://drive.google.com/drive/u/2/folders/{FID}", "folder"),
    (f"https://docs.google.com/file/d/{FID}/edit", "file"),
    (f"  {FID}  ", "unknown"),
])
def test_ti7_accepted_forms_give_the_id(text, kind):
    """A developer pastes whichever link form Drive gave them."""
    ref = parse_drive_link(text)
    assert ref.id == FID and ref.kind == kind


@pytest.mark.parametrize("text", [
    "http://127.0.0.1/x",
    "file:///etc/passwd",
    f"https://drive.google.com.evil.io/file/d/{FID}",
    f"https://evil.io/?u=https://drive.google.com/file/d/{FID}",
    f"https://drive.google.com@evil.io/file/d/{FID}",
    f"https://evil.io\\@drive.google.com/file/d/{FID}",
    f"http://drive.google.com/file/d/{FID}",
    f"https://drive.google.com:8443/file/d/{FID}",
    f"https://user:pw@drive.google.com/file/d/{FID}",
    "https://drive.google.com/drive/my-drive",
    "https://drive.google.com/file/d/short",
    f"https://drive.google.com/open?id={FID}&id={FID}",
    "https://drive.google.com/open",
    f"https://www.google.com/file/d/{FID}",
    f"https://DRIVE.GOOGLE.COM.evil.io/file/d/{FID}",
    f"https://drive.google.com/file/d/{FID}\n/../../x",
    f"https://drive.google.com/file/d/{FID}/\u202e",
    "https://169.254.169.254/latest/meta-data",
    "../../etc/passwd", "C:\\x", "abc", "a b c d e f g", "", "   ",
])
def test_ti7_ho32_every_other_shape_is_refused(text):
    """HO32's named hostile links, plus userinfo, ports, control and bidi characters."""
    with pytest.raises(DriveLinkError):
        parse_drive_link(text)


def test_refusal_never_echoes_the_pasted_text():
    """A link can carry an access token in its query; the refusal must not repeat it."""
    secret = "ya29.CANARY-TOKEN-1234567890"
    with pytest.raises(DriveLinkError) as caught:
        parse_drive_link(f"https://evil.io/x?access_token={secret}")
    assert secret not in str(caught.value) and "evil.io" not in str(caught.value)
