"""TA12 (CRITICAL): no secret and no product data leaves where it must not. After a press, a
scheduled run, an intake, a review and a share the secret canary is absent from every file under
the data root except the fixture `.env`, from every page the rig fetched, from the provider
request log, from captured logs and from stdout/stderr; the page canary is absent from the
outbox."""

from __future__ import annotations

import logging

from review_support import grant_review, review, upload_video
from rig import CANARY_PAGE, CANARY_SECRET, HTML, SLUG, World, press
from schedule_support import SLOT, schedule

from autotester.stages.bug_run import process_run
from autotester.stages.schedule_wiring import tick_all
from autotester.ui.run_queue import get_queue

PAGES = ["/", "/projects/{slug}", "/projects/{slug}/env", "/projects/{slug}/sources",
         "/projects/{slug}/cases", "/projects/{slug}/report", "/projects/{slug}/flowspec",
         "/admin/users", "/admin/groups", "/access-requests"]


def exercise(world: World) -> list[str]:
    """Every scenario once; returns the bodies of the pages fetched along the way, except the
    Credentials page as seen by its `credentials.view` holder (admin): that page shows the stored
    value in an edit box BY DESIGN (auth.md AU27). It is asserted separately below."""
    schedule(world)
    run_id = press(world, "dev")
    process_run(world.store(), world.bugs(), run_id)
    tick_all(SLOT, root=world.root, queue=get_queue())
    source = upload_video(world, "dev")
    grant_review(world)
    review(world, source, "1:00 | total")
    world.users["dev"].post(f"/projects/{SLUG}/videos/{source.id}/share-link")
    bodies = []
    for who in ("admin", "dev", "subadmin"):
        for path in [*PAGES, f"/projects/{SLUG}/runs/{run_id}"]:
            if who == "admin" and path.endswith("/env"):
                continue
            bodies.append(world.users[who].get(path.format(slug=SLUG), headers=HTML).text)
    return bodies


def test_the_secret_canary_is_nowhere_it_must_not_be(world: World, caplog, capfd) -> None:
    caplog.set_level(logging.DEBUG)
    bodies = exercise(world)
    assert any(bodies)
    leaks = [str(p.relative_to(world.root)) for p in sorted(world.root.rglob("*"))
             if p.is_file() and p.name != ".env"
             and CANARY_SECRET.encode() in p.read_bytes()]
    assert leaks == []
    assert not any(CANARY_SECRET in body for body in bodies)
    assert not any(CANARY_SECRET in prompt for prompt in world.provider.prompts)
    assert CANARY_SECRET not in caplog.text
    out = capfd.readouterr()
    assert CANARY_SECRET not in out.out + out.err


def test_the_page_canary_never_reaches_the_outbox_or_the_provider_log(world: World) -> None:
    exercise(world)
    assert not any(CANARY_PAGE.encode() in p.read_bytes() for p in world.outbox.glob("*"))
    assert not any(CANARY_PAGE in prompt for prompt in world.provider.prompts)


def test_only_a_credentials_view_holder_is_shown_the_value_on_the_credentials_page(
        world: World) -> None:
    """The one place the value is rendered is the edit box for `credentials.view` (admin); the
    developer and sub-admin never see it, and neither does the tester or the pending account."""
    env = f"/projects/{SLUG}/env"
    for who in ("dev", "subadmin", "tester", "pending"):
        assert CANARY_SECRET not in world.users[who].get(env, headers=HTML).text
