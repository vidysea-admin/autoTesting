"""hosting.md HO1, HO2, HO6, HO7, HO9, HO14: the deploy files cannot leak a secret, publish a
raw port, drift from the code's env keys, or pin a different Playwright than the lockfile.

Scenarios: a developer adds a feature that reads a new env key; someone pastes a password into
the compose file; someone bumps `uv.lock` without bumping the Dockerfile base image.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

import pytest
import yaml

from autotester.auth.config import AuthConfigError, check_startup

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
        if body.endswith("/"):                      # a directory
            name = body.rstrip("/")
            hit = name in parts[:-1] if anywhere else path.startswith(name + "/")
        else:
            names = parts if anywhere else [path]
            hit = any(fnmatch.fnmatch(n, body) for n in names)
        if hit:
            ignored = not negate
    return ignored


# hosting.md HO1 names these six; the older six are kept (git metadata, a nested .env, ...).
_HO1_CANARIES = (".env", ".env.local", "projects/x/runs/r1/secret.txt", "profiles/x/Cookies",
                 ".work/auth/users.json", ".work/audit.jsonl")
_EXTRA_CANARIES = ("projects/pathlynks/project.json", "profiles/a/state.json", "nested/.env",
                   ".work/run_queue.json", ".git/config", "qa/evidence/shot.png")


def test_dockerignore_keeps_secrets_and_project_state_out_of_the_image() -> None:
    """Someone builds the image on the server with `COPY . .`: every canary a leak would come
    from must be ignored, and dropping any one rule (e.g. `**/.env.*`) must turn this red."""
    patterns = [ln.strip() for ln in (ROOT / ".dockerignore").read_text(encoding="utf-8")
                .splitlines() if ln.strip() and not ln.startswith("#")]
    for canary in _HO1_CANARIES + _EXTRA_CANARIES:
        assert _ignored(canary, patterns), f"{canary} would ship in the image"
    assert not _ignored(".env.example", patterns)
    assert not _ignored("src/autotester/ui/app.py", patterns)


def test_the_canary_check_itself_notices_a_dropped_rule() -> None:
    """The matcher is only a guard if removing a rule changes its answer (AT-862)."""
    patterns = [ln.strip() for ln in (ROOT / ".dockerignore").read_text(encoding="utf-8")
                .splitlines() if ln.strip() and not ln.startswith("#")]
    without = [p for p in patterns if p != "**/.env.*"]
    assert _ignored(".env.local", patterns) and not _ignored(".env.local", without)


def test_compose_needs_no_domain_unless_the_https_profile_is_used() -> None:
    """AT-864: an operator following DEPLOY.md step 8 (no domain yet) runs `docker compose
    config` / `up`. Compose interpolates every service, profile or not, so a required-variable
    form (`${AUTOTESTER_DOMAIN:?...}`) on the caddy service fails the loopback path with rc=1."""
    text = (ROOT / "docker" / "compose.prod.yml").read_text(encoding="utf-8")
    assert re.search(r"\$\{AUTOTESTER_DOMAIN:-[^}]+\}", text)
    assert "${AUTOTESTER_DOMAIN:?" not in text
    assert _prod()["services"]["caddy"]["profiles"] == ["https"]


def test_app_service_is_told_its_public_origin_for_the_wildcard_bind() -> None:
    """AU20 (owner gate answer, D-082): the app binds 0.0.0.0 and cannot know the address users
    open, so compose passes AUTOTESTER_PUBLIC_ORIGIN to the app service, derived from the domain."""
    env = _prod()["services"]["autotester"]["environment"]
    assert "AUTOTESTER_DOMAIN" in env["AUTOTESTER_PUBLIC_ORIGIN"]
    assert env["AUTOTESTER_PUBLIC_ORIGIN"].count("${") == 3  # operator value, domain test, domain
    guide = (ROOT / "docker" / "DEPLOY.md").read_text(encoding="utf-8")
    assert "AUTOTESTER_PUBLIC_ORIGIN" in guide and "AUTOTESTER_PUBLIC_ORIGIN" in (
        ROOT / ".env.example").read_text(encoding="utf-8")


def _interpolate(value: str, env: dict[str, str]) -> str:
    """Compose interpolation (compose-spec "Interpolation") for the forms the file uses,
    innermost first: `${V}` is V's value; `${V:-d}` is d when V is unset or empty; `${V:+a}` is
    a when V is set and non-empty, else empty. No docker needed."""
    pattern = re.compile(r"\$\{(\w+)(?::([-+])([^${}]*))?\}")
    while (m := pattern.search(value)):
        name, op, alt = m.groups()
        got = env.get(name, "")
        out = got if op is None else (got or alt) if op == "-" else (alt if got else "")
        value = value[:m.start()] + out + value[m.end():]
    return value


def _wildcard_startup(monkeypatch: pytest.MonkeyPatch, compose_env: dict[str, str],
                      hosts: str, origins: str) -> None:
    """What `docker/entrypoint.sh` does: bind 0.0.0.0, hosted, with the origin compose hands
    the app for this operator environment."""
    value = _interpolate(
        _prod()["services"]["autotester"]["environment"]["AUTOTESTER_PUBLIC_ORIGIN"],
        compose_env)
    for key in ("AUTOTESTER_AUTH_DISABLED", "UVICORN_PORT"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("AUTOTESTER_HOSTED", "1")
    monkeypatch.setenv("AUTOTESTER_FIRST_ADMIN_EMAIL", "boss@at.example")
    monkeypatch.setenv("AUTOTESTER_ALLOWED_HOSTS", hosts)
    monkeypatch.setenv("AUTOTESTER_ALLOWED_ORIGINS", origins)
    monkeypatch.setenv("AUTOTESTER_PUBLIC_ORIGIN", value)
    monkeypatch.setattr("sys.argv", ["uvicorn", "app", "--host", "0.0.0.0", "--port", "8000"])


def test_compose_default_public_origin_is_empty_without_a_domain() -> None:
    """AU20(b): with neither variable set compose must not invent an origin (it once invented
    `https://localhost`, which the guards admit, so the 'required' rule could never fire)."""
    raw = _prod()["services"]["autotester"]["environment"]["AUTOTESTER_PUBLIC_ORIGIN"]
    assert _interpolate(raw, {}) == ""
    assert _interpolate(raw, {"AUTOTESTER_DOMAIN": "qa.example.com"}) == "https://qa.example.com"
    assert _interpolate(raw, {"AUTOTESTER_DOMAIN": "q.x", "AUTOTESTER_PUBLIC_ORIGIN":
                              "http://10.0.0.5:8000"}) == "http://10.0.0.5:8000"
    assert "localhost" not in raw


@pytest.mark.parametrize(("compose_env", "hosts", "origins"), [
    pytest.param({}, "other.example.com", "https://other.example.com", id="nothing-set"),
    pytest.param({}, "192.168.1.99:8000", "http://192.168.1.99:8000", id="interim-wrong-ip"),
])
def test_compose_default_fed_through_startup_raises_on_a_list_naming_nothing_useful(
        monkeypatch: pytest.MonkeyPatch, compose_env: dict[str, str], hosts: str,
        origins: str) -> None:
    """AU20(b), the shipped container path: the default compose produces, on a 0.0.0.0 bind
    with an allow-list that does not name the server, is refused at startup, not served as 403."""
    _wildcard_startup(monkeypatch, compose_env, hosts, origins)
    with pytest.raises(AuthConfigError, match="AUTOTESTER_PUBLIC_ORIGIN is required"):
        check_startup()


def test_compose_domain_fed_through_startup_starts_only_when_the_lists_name_it(
        monkeypatch: pytest.MonkeyPatch) -> None:
    env = {"AUTOTESTER_DOMAIN": "qa.example.com"}
    _wildcard_startup(monkeypatch, env, "", "https://qa.example.com")
    check_startup()
    _wildcard_startup(monkeypatch, env, "other.example.com", "https://other.example.com")
    with pytest.raises(AuthConfigError, match="is not allowed"):
        check_startup()


def test_deploy_guide_claims_only_what_the_compose_file_does() -> None:
    """AT-864: the guide once sent operators to an SSH tunnel to 6080, which compose only
    `expose`s (nothing listens on the host), and described a Host allow-list (AT-758) that is
    not in the code as if it answered 403 today. AT-758 has since landed, so the guide now says
    the allow-list answers 403 and no longer says it is missing from the release."""
    guide = (ROOT / "docker" / "DEPLOY.md").read_text(encoding="utf-8")
    assert "http://localhost:6080" not in guide
    assert "ships with AT-758" not in guide and "AT-758 is in your release" not in guide
    assert "empty 403" in guide
    assert "AUTOTESTER_ALLOWED_HOSTS" in guide
