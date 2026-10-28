"""T-174 CM5 (qa/contracts/cli-mcp.md): `mcp_server` is a thin adapter and `mcp` is declared.

Split out of test_cli_mcp.py to keep that file under the C2 300-line cap; no fixtures needed.
"""

from __future__ import annotations

from pathlib import Path

from autotester import mcp_server


def test_mcp_module_is_a_thin_adapter() -> None:
    source = Path(mcp_server.__file__).read_text(encoding="utf-8")
    imported = {line.split()[1] for line in source.splitlines() if line.startswith("from ")}
    assert imported == {"__future__", "mcp.server.mcpserver", "autotester.schema.catalog",
                        "autotester.schema.cli_output", "autotester.stages"}
    assert "launch_run" not in source and "BrowserSession" not in source


def test_mcp_dependency_is_declared() -> None:
    text = (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    assert '"mcp>=' in text
