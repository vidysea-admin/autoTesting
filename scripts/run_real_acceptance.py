"""T-169 GR1-GR4: drive one acceptance mode against a REAL, already-onboarded project.

    PYTHONPATH=src python scripts/run_real_acceptance.py <slug> --mode teaching|url_only
        [--max-actions N] [--wall-clock S] [--dry-run] [--root DIR]

Refuses to start without the signed approvals the mode needs (prints the grant command).
`--dry-run` checks approvals and prints the plan only: no browser, no model. Otherwise it
drives `run_mode` through the app's routes with real seams, writes
qa/evidence/t169-real/<mode>/ and prints the GR1-GR4 checklist. Umesh's verdict (GR3) and the
AT-281 thresholds are never computed. The sign-in is AUTOTESTER_HARNESS_EMAIL and
AUTOTESTER_HARNESS_PASSWORD from the repo-root .env, entered on the settings page; there is no
terminal prompt. Contract: qa/contracts/generic-acceptance.md.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from autotester.core.consent import ApprovalRequired
from autotester.core.env import HARNESS_KEYS, load_repo_env
from autotester.core.paths import repo_root
from autotester.schema.crawl import CrawlBounds
from autotester.stages.generic_acceptance import ModeSeams, ModeSpec
from autotester.stages.real_acceptance import (
    acceptance_client,
    crawl_bounds,
    drive_real,
    preflight,
    require_fresh_baseline,
    required_kinds,
)
from autotester.store.project_store import ProjectStore


def _real_seams(store: ProjectStore, mode: str, bounds: CrawlBounds) -> ModeSeams:
    """Real model and browser contact points (never built in --dry-run or in tests)."""
    from autotester import providers
    from autotester.browser.secrets import SecretStore
    from autotester.cli_orchestrate import _make_crawl_fn

    project = store.load_project()
    assert project is not None
    if mode == "teaching":
        return ModeSeams(ingest_provider=providers.for_role(project, "vision"))
    secrets = SecretStore.load(project, store.paths.env_file, strict=False)
    return ModeSeams(crawl_fn=_make_crawl_fn(
        project, store, store.paths, secrets, bounds, None))


def _harness_login() -> tuple[str, str] | None:
    """The AutoTester login from the repo-root `.env` (settings page), or None after naming
    the missing KEY on stderr. Never prompts; values are never printed."""
    missing = [key for key in HARNESS_KEYS if not os.environ.get(key, "").strip()]
    if missing:
        origin = os.environ.get("AUTOTESTER_PUBLIC_ORIGIN", "").strip() or "http://127.0.0.1:8000"
        print(f"MISSING {', '.join(missing)}: enter it on the AutoTester settings page, "
              f"{origin.rstrip('/')}/settings/providers", file=sys.stderr)
        return None
    return os.environ[HARNESS_KEYS[0]].strip(), os.environ[HARNESS_KEYS[1]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("slug")
    parser.add_argument("--mode", required=True, choices=["teaching", "url_only"])
    parser.add_argument("--dry-run", action="store_true",
                        help="check approvals and print the plan; start nothing")
    parser.add_argument("--max-actions", type=int, default=None,
                        help="url_only crawl action cap (default: fit the covering approval)")
    parser.add_argument("--wall-clock", type=float, default=None,
                        help="url_only crawl seconds (default: fit the covering approval)")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = (args.root or repo_root()).resolve()
    os.environ["AUTOTESTER_ROOT"] = str(root)
    load_repo_env(root)  # AT-110: the approval key lives in the repo-root .env, as for the CLI
    store = ProjectStore(args.slug, root)
    project = store.load_project()
    if project is None:
        print(f"project {args.slug!r} is not onboarded under {root}", file=sys.stderr)
        return 2
    try:
        require_fresh_baseline(store, args.mode)
        bounds = (crawl_bounds(store, args.max_actions, args.wall_clock)
                  if args.mode == "url_only" else None)
        ids = preflight(store, args.mode, bounds)
    except (ApprovalRequired, ValueError) as why:
        print(f"REFUSED: {why}", file=sys.stderr)
        return 3
    print(f"approvals OK for {[k.value for k in required_kinds(args.mode)]}: {ids}")
    if bounds is not None:
        print(f"crawl bounds: max_actions={bounds.max_actions} wall_clock_s={bounds.wall_clock_s}")
    if args.dry_run:
        print(f"dry run: would drive {args.mode} on {project.base_url}; nothing started")
        return 0
    login = _harness_login()
    if login is None:
        return 4
    from autotester.ui.app import app

    spec = ModeSpec(mode=args.mode, slug=args.slug, name=project.name, base_url=project.base_url,
                    allowed_domains=list(project.allowed_domains), onboard=False)
    try:
        with acceptance_client(app, *login, args.slug) as client:
            login = None
            seams = _real_seams(store, args.mode, bounds or CrawlBounds())
            _, out, lines = drive_real(client, store, spec, seams, root, bounds=bounds)
    except ValueError as why:
        print(f"REFUSED: {why}", file=sys.stderr)
        return 3
    print(f"evidence: {out}")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
