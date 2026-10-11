#!/usr/bin/env bash
# usage: run.sh <script.py> ; T204B_BASE must be exported
export PYTHONPATH=D:/autoTesting/.worktrees/t204-team-login/src
export PYTHONIOENCODING=utf-8
exec D:/autoTesting/.worktrees/t204-team-login/.venv/Scripts/python.exe "$@"
