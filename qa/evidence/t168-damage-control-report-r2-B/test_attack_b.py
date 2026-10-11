"""Seat B throwaway attacks on DC4 (never in the worktree)."""
from __future__ import annotations

import html as htmllib
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

import test_unified_report_secrets as tus
from autotester.cli import app as cli_app
from autotester.stages.unified_report import build_report
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app as ui_app

REPO = tus.REPO
runner = CliRunner()
LOG = Path(os.environ["ATTACK_LOG"])


def log(msg: str) -> None:
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(msg + "\n")


def forms(s: str) -> list[str]:
    return [s, htmllib.escape(s), htmllib.escape(s, quote=False), urllib.parse.quote(s),
            urllib.parse.quote(s, safe=""), json.dumps(s)[1:-1]]


def env_line(s: str) -> str:
    q = "'" if '"' in s else '"'
    return f"DEMO_PASSWORD={q}{s}{q}\n"


SECRETS = ["a.b*c(d)[e]{f}$^|x\\y", "pässwörd✓€", 'x<b>&amp;"z', "Hunter2Pass",
           "tok=abc/def+ghi==", "p&ss<w>o'rdQ9"]


@pytest.mark.parametrize("secret", SECRETS)
def test_success_path(secret: str, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    tmp_path = tmp_path_factory.mktemp("w")
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    (tmp_path / ".env").write_text(env_line(secret), encoding="utf-8")
    monkeypatch.setattr(tus, "S", secret)
    tus._seed_everywhere(tmp_path)
    out = tmp_path / "o.html"
    res = runner.invoke(cli_app, ["release-report", "demo", "--out", str(out)])
    assert res.exit_code == 0, res.output
    page = out.read_text(encoding="utf-8")
    route = TestClient(ui_app, raise_server_exceptions=False).get("/projects/demo/damage-report")
    route2 = TestClient(ui_app, raise_server_exceptions=False).get(
        "/projects/demo/damage-report?run=rel1")
    env = {**os.environ, "AUTOTESTER_ROOT": str(tmp_path)}
    scan = subprocess.run([sys.executable, str(REPO / "scripts/check_no_secrets.py"), str(out)],
                          env=env, capture_output=True, text=True)
    leaks = [(n, f) for f in forms(secret) for n, t in
             (("cli_html", page), ("cli_out", res.output), ("route", route.text),
              ("route_run", route2.text)) if f in t]
    log(f"SUCCESS secret={secret!r} cli={res.exit_code} route={route.status_code}/"
        f"{route2.status_code} scanner={scan.stdout.strip()!r} leaks={leaks}")
    assert "0 leak(s)" in scan.stdout
    # percent-encoded or other transformed forms are recorded, only exact/escaped forms assert
    hard = [(n, f) for n, f in leaks if f in (secret, htmllib.escape(secret))]
    assert not hard, hard


def _variants(path: Path, secret: str):
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(raw)
        if isinstance(data, dict):
            yield "extra-key", json.dumps({**data, secret: secret})
            yield "all-fields-secret", json.dumps({k: secret for k in data})
            for k in list(data)[:12]:
                yield f"field-{k}", json.dumps({**data, k: secret})
            yield "nested-key", json.dumps({k: ({secret: secret} if isinstance(v, (dict, list))
                                                else v) for k, v in data.items()})
        yield "truncated", raw[: max(5, len(raw) // 2)] + secret
        yield "secret-only", secret
    else:
        lines = raw.splitlines()
        for idx in range(min(len(lines), 3)):
            row = json.loads(lines[idx])
            for tag, newrow in (("extra-key", {**row, secret: secret}),
                                ("all-fields", {k: secret for k in row})):
                new = list(lines)
                new[idx] = json.dumps(newrow)
                yield f"line{idx}-{tag}", "\n".join(new) + "\n"
            for k in list(row)[:8]:
                new = list(lines)
                new[idx] = json.dumps({**row, k: secret})
                yield f"line{idx}-{k}", "\n".join(new) + "\n"
        yield "garbage-line", raw + secret + "\n"
        yield "truncated", raw[: max(5, len(raw) // 2)] + secret


@pytest.mark.parametrize("secret", ["p&ss<w>o'rdQ9", "Hunter2Pass", "pässwörd✓€"])
def test_error_paths(secret: str, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    tmp_path = tmp_path_factory.mktemp("w")
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    (tmp_path / ".env").write_text(env_line(secret), encoding="utf-8")
    monkeypatch.setattr(tus, "S", secret)
    tus._seed_everywhere(tmp_path)
    proj = tmp_path / "projects" / "demo"
    files = sorted(p for p in proj.rglob("*") if p.is_file() and p.suffix in (".json", ".jsonl"))
    log(f"ERRFILES secret={secret!r}: {[str(p.relative_to(proj)) for p in files]}")
    client = TestClient(ui_app, raise_server_exceptions=False)
    bad: list[str] = []
    n = 0
    for path in files:
        original = path.read_bytes()
        for tag, content in _variants(path, secret):
            n += 1
            path.write_text(content, encoding="utf-8")
            outs: dict[str, str] = {}
            res = runner.invoke(cli_app, ["release-report", "demo", "--out",
                                          str(tmp_path / "o.html")])
            outs["cli"] = res.output + (res.stderr_bytes or b"").decode("utf-8", "replace")
            if res.exception is not None and not isinstance(res.exception, SystemExit):
                outs["cli_exc"] = repr(res.exception) + "".join(
                    __import__("traceback").format_exception(res.exception))
            r = client.get("/projects/demo/damage-report")
            outs["route"] = r.text
            r2 = client.get("/projects/demo/damage-report?run=rel1")
            outs["route_run"] = r2.text
            try:
                build_report(ProjectStore("demo", tmp_path), None)
            except Exception as exc:  # noqa: BLE001
                outs["build"] = f"{type(exc).__name__}: {exc}"
            if (tmp_path / "o.html").exists():
                outs["html"] = (tmp_path / "o.html").read_text(encoding="utf-8")
                (tmp_path / "o.html").unlink()
            for name, text in outs.items():
                for f in forms(secret):
                    if f in text:
                        bad.append(f"{path.name}/{tag}/{name}: form {f!r}")
                if "input_value" in text:
                    bad.append(f"{path.name}/{tag}/{name}: input_value")
            if "cli_exc" in outs:
                bad.append(f"{path.name}/{tag}: CLI uncaught {outs['cli_exc'][:200]!r}")
            log(f"ERR {secret!r} {path.name}/{tag}: cli={res.exit_code} route={r.status_code}"
                f"/{r2.status_code} build={outs.get('build', 'ok')[:110]!r}")
        path.write_bytes(original)
    log(f"ERRVARIANTS secret={secret!r} ran={n} bad={len(bad)}")
    for b in bad:
        log("BAD " + b)
    assert not bad, bad[:10]


def test_percent_encoded_url_in_stored_network(tmp_path: Path,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    s = "p&ss<w>o'rdQ9"
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    (tmp_path / ".env").write_text(env_line(s), encoding="utf-8")
    store = tus._seed_everywhere(tmp_path)
    from autotester.schema.enums import EvidenceKind
    from autotester.schema.run import Evidence
    store.add_crawl_network("cr1", Evidence(kind=EvidenceKind.NETWORK,
                            path=f"GET https://demo.test/g?pw={urllib.parse.quote(s)} -> 500"))
    page = build_report(store, None).model_dump_json()
    html = __import__("autotester.stages.unified_report", fromlist=["x"]).unified_html(store)
    log(f"PCT encoded url: in_object={urllib.parse.quote(s) in page} in_html="
        f"{urllib.parse.quote(s) in html} raw_in_html={s in html}")
