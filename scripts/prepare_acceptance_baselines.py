"""Prepare isolated input-only acceptance baselines from a frozen explicit plan; no live calls."""

import argparse
from pathlib import Path

from autotester.schema.acceptance_baseline import BaselinePlan
from autotester.stages.acceptance_baseline import prepare_baselines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    plan = BaselinePlan.model_validate_json(args.plan.read_bytes())
    prepare_baselines(args.source_root, args.input_root, args.destination, plan)
    print("Prepared local baselines; authorized credential context and production approvals "
          "remain required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
