"""hosting.md HO1, HO2, HO6, HO7, HO9, HO14: the deploy files cannot leak a secret, publish a
raw port, drift from the code's env keys, or pin a different Playwright than the lockfile.

Scenarios: a developer adds a feature that reads a new env key; someone pastes a password into
the compose file; someone bumps `uv.lock` without bumping the Dockerfile base image.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW_PORTS = {"8000", "8010", "6080", "5900"}
SECRET_LOOKING = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY|"
    r"(?i:password|secret|token|api_key)\s*[:=]\s*['\"]?[A-Za-z0-9/+_-]{8,})")


def _prod() -> dict:
    return yaml.safe_load((ROOT / "docker" / "compose.prod.yml").read_text(encoding="utf-8"))


def test_prod_compose_publishes_the_app_on_loopback_only_and_never_a_raw_port() -> None:
    services = _prod()["services"]
    for name, svc in services.items():
        for port in svc.get("ports", []):
            text = str(port)
            if name == "autotester":
                assert text.startswith("${AUTOTESTER_BIND:-127.0.0.1}:"), text
            else:
                assert text.split(":")[-1] in {"80", "443"}, text
            assert not (RAW_PORTS & set(re.split(r"[:/]", text))) or name == "autotester"
    assert "6080" not in " ".join(map(str, services["autotester"].get("ports", [])))
    assert "5900" not in yaml.safe_dump(services)


def test_prod_compose_is_hardened_and_does_not_mount_the_source_tree() -> None:
    svc = _prod()["services"]["autotester"]
    assert svc["restart"] == "unless-stopped" and svc["init"] is True
    assert "no-new-privileges:true" in svc["security_opt"]
    assert svc["logging"]["options"]["max-size"] and svc["healthcheck"]["test"]
    assert svc["mem_limit"] and svc["cpus"] and svc["shm_size"]
    mounts = [str(v) for v in svc["volumes"]]
    assert mounts and all(m.endswith(":/data") for m in mounts)      # data root only, no `.:/app`
    assert svc["environment"]["AUTOTESTER_ROOT"] == "/data"


def test_no_secret_value_anywhere_under_docker_or_in_the_dockerfile() -> None:
    files = [p for p in (ROOT / "docker").rglob("*") if p.is_file()] + [ROOT / "Dockerfile"]
    for path in files:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("#"):
                continue
            assert not SECRET_LOOKING.search(line), f"{path.name}: {line.strip()[:60]}"


def test_env_example_documents_every_key_the_code_reads() -> None:
    documented = set(re.findall(r"^#?\s*(AUTOTESTER_[A-Z_]+)=", (ROOT / ".env.example")
                               .read_text(encoding="utf-8"), re.M))
    used = set()
    for path in (ROOT / "src").rglob("*.py"):
        used |= set(re.findall(r"AUTOTESTER_[A-Z_]+[A-Z]", path.read_text(encoding="utf-8")))
    assert used - documented == set(), f"undocumented env keys: {sorted(used - documented)}"
    assert {"AUTOTESTER_ALLOWED_HOSTS", "AUTOTESTER_ALLOWED_ORIGINS",
            "AUTOTESTER_MAX_CONCURRENT_RUNS"} <= documented


def test_env_example_holds_no_secret_looking_value() -> None:
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or "=" not in line:
            continue
        value = line.split("=", 1)[1].strip()
        assert not SECRET_LOOKING.search(line), line
        assert value == "" or len(value) < 12 or value.isdigit(), line


def test_dockerfile_playwright_tag_equals_the_locked_version() -> None:
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    locked = re.search(r'name = "playwright"\nversion = "([\d.]+)"', lock).group(1)
    tag = re.search(r"playwright/python:v([\d.]+)", (ROOT / "Dockerfile").read_text(
        encoding="utf-8")).group(1)
    assert tag == locked


def _ignored(path: str, patterns: list[str]) -> bool:
    """Last matching rule wins (`!` re-includes), like a real .dockerignore for these shapes."""
    parts = path.split("/")
    ignored = False
    for pat in patterns:
        negate = pat.startswith("!")
        body = pat.lstrip("!")
        anywhere = body.startswith("**/")
        body = body.removeprefix("**/")
        if body.endswith("/"):                      # a directory: any ancestor named so
            names = parts[:-1] if anywhere else parts[:1]
            hit = body.rstrip("/") in names
        else:
            names = parts if anywhere else [path]
            hit = any(fnmatch.fnmatch(n, body) for n in names)
        if hit:
            ignored = not negate
    return ignored


def test_dockerignore_keeps_secrets_and_project_state_out_of_the_image() -> None:
    patterns = [ln.strip() for ln in (ROOT / ".dockerignore").read_text(encoding="utf-8")
                .splitlines() if ln.strip() and not ln.startswith("#")]
    for canary in (".env", "projects/pathlynks/project.json", "profiles/a/state.json",
                   "nested/.env", ".work/run_queue.json", ".git/config"):
        assert _ignored(canary, patterns), f"{canary} would ship in the image"
    assert not _ignored(".env.example", patterns)
    assert not _ignored("src/autotester/ui/app.py", patterns)
