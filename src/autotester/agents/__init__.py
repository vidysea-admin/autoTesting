"""The agent layer (T-179, D-042): the lead tester's tool surface over the existing stages.

This slice holds the part that does not need a model framework: `context.py` (what a model
can never choose), `guards.py` (the checks that run in code) and `tools.py` (the stage tools
and their one dispatcher). The planner, subagents and `skills=` loading are the framework's
and arrive with the rest of T-179.
"""
