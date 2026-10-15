"""Dry-run exact legacy provider plans; apply/restore only explicitly selected checked plans."""
import argparse
from pathlib import Path

from autotester.providers.config_migration import change_legacy_roles, plan_legacy_roles
from autotester.schema.provider_migration import ProviderMigrationPlan
from autotester.store.filestore import write_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--project", action="append", default=[])
    parser.add_argument("--plan", type=Path, required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    if not args.project:
        parser.error("explicit --project selections are required")
    if args.apply or args.restore:
        plan = ProviderMigrationPlan.model_validate_json(args.plan.read_bytes())
        rows = change_legacy_roles(args.root, plan, args.project, restore=args.restore)
        for row in rows:
            print(row.model_dump_json())
        if any(row.status == "stale" for row in rows):
            raise SystemExit(1)
    else:
        if args.plan.exists():
            parser.error("refusing to overwrite an existing plan")
        plan = plan_legacy_roles(args.root, args.project)
        write_bytes(args.plan, plan.model_dump_json(indent=2).encode())
        print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
