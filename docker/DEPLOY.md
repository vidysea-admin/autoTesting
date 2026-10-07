# Hosting AutoTester on a server

Contract: `qa/contracts/hosting.md` HO11. Decisions: D-071, D-072. This guide has no secret
values and no real hostnames in it; replace every `<angle-bracket>` placeholder.

What you end up with: one container running the web UI on port 8000 (and an internal noVNC
viewer), your data in one folder on the host, optional HTTPS through Caddy, and a run queue
that lets at most **2** runs execute at once (one per project) and shows the rest as `queued`.

## Part A: Ubuntu server (production)

Ubuntu 22.04 or 24.04 LTS, 4 vCPU and 8 GB RAM or more (a headed Chromium per run needs about
1.5 GB; the default limit of 2 concurrent runs fits).

### 1. Prerequisites

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl git ufw
curl -fsSL https://get.docker.com | sudo sh          # Docker Engine + compose plugin
sudo usermod -aG docker "$USER" && newgrp docker
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw enable
```

Do **not** open 8000, 8010, 6080 or 5900 in the firewall. Only 22, 80 and 443 are public.

### 2. Get the code and build from a tag

```bash
git clone https://github.com/umeshsugara-ai/autoTesting.git && cd autoTesting
git checkout <release-tag>
```

The image is built on the server (`docker compose ... --build`), so the Playwright base image
tag in the `Dockerfile` always matches `uv.lock` (a test enforces it).

### 3. The two env files

There are two, with different jobs. Neither is ever committed.

| File | Holds | Where |
|---|---|---|
| `/etc/autotester/server.env` | server settings (this guide) | on the host, mode 600 |
| `<data>/.env` | provider keys and each project's test-account credentials | inside the data folder |

```bash
sudo mkdir -p /etc/autotester /srv/autotester/data/projects /srv/autotester/data/profiles
sudo cp .env.example /etc/autotester/server.env && sudo chmod 600 /etc/autotester/server.env
sudo cp .env.example /srv/autotester/data/.env   && sudo chmod 600 /srv/autotester/data/.env
sudo chown -R 1000:1000 /srv/autotester/data      # adjust if your container user differs
```

Edit `/etc/autotester/server.env` and set at least:

```
AUTOTESTER_ALLOWED_HOSTS=<your-domain-or-ip>
AUTOTESTER_ALLOWED_ORIGINS=https://<your-domain>
AUTOTESTER_MAX_CONCURRENT_RUNS=2
```

`AUTOTESTER_ALLOWED_HOSTS` and `AUTOTESTER_ALLOWED_ORIGINS` are **required** once the server is
reachable by name: without them the Host allow-list (AT-758) and Origin guard (D-066) answer
every request with 403. Put the model keys (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`) and
`AUTOTESTER_APPROVAL_KEY` in `<data>/.env`.

### 4. Seed your projects (optional)

Copy existing `projects/<slug>/` and `profiles/<slug>/` folders from your dev machine into
`/srv/autotester/data/`. Credentials stay in `<data>/.env`, never inside a project folder.

### 5. Create the first account BEFORE exposing the port

Sign-in arrives with T-204. When it is in your release, set `AUTOTESTER_FIRST_ADMIN_EMAIL` and
`AUTOTESTER_HOSTED=1` in `server.env`, start the stack bound to loopback (step 6, default), and
create the administrator over an SSH tunnel (`ssh -L 8000:localhost:8000 <server>`, then open
`http://localhost:8000`). Only then open it to the network. Until accounts exist in your
release, keep the stack on loopback and use the SSH tunnel for everything.

### 6. Start

```bash
docker compose -f docker/compose.prod.yml up -d --build                 # loopback only
docker compose -f docker/compose.prod.yml --profile https up -d --build # + HTTPS (step 7)
docker compose -f docker/compose.prod.yml ps                            # wait for "healthy"
curl -fsS http://127.0.0.1:8000/healthz
```

### 7. HTTPS

With a DNS name pointing at the server, set `AUTOTESTER_DOMAIN=<your-domain>` in the shell (or a
`.env` next to the compose file) and use the `https` profile above. Caddy gets and renews the
certificate itself, sets security headers, and limits request bodies to
`AUTOTESTER_MAX_UPLOAD_BYTES`. Prefer your own nginx? Proxy to `127.0.0.1:8000`, forward `Host`
and `X-Forwarded-Proto`, and set `client_max_body_size` to the same upload limit.

The live browser view (`/novnc/*`) answers 503 through Caddy until sign-in is enabled (T-204
wires the check); on a trusted network use the SSH tunnel and `http://localhost:6080`.

### 8. Interim without a domain

Over plain http to an IP, set in `server.env`: `AUTOTESTER_ALLOWED_HOSTS=<server-ip>`,
`AUTOTESTER_ALLOWED_ORIGINS=http://<server-ip>:8000`, `AUTOTESTER_COOKIE_SECURE=0`, and start
with `AUTOTESTER_BIND=0.0.0.0` (then `ufw allow from <your-office-ip> to any port 8000`). Passwords
cross the network unencrypted in this mode: use it for a short trial only, and move to step 7.

### 9. Backup and restore

All state is in `/srv/autotester/data`: `projects/`, `profiles/` (logged-in browser sessions),
`.env`, and `.work/` (the run queue and server settings).

```bash
sudo tar czf /var/backups/autotester-$(date +%F).tgz -C /srv/autotester data
# restore: stop the stack, extract over /srv/autotester, start again
```

Keep the archive off the server and treat it as a secret (it holds credentials and sessions).

### 10. Upgrade and rollback

```bash
git fetch --tags && git checkout <new-tag>
docker compose -f docker/compose.prod.yml up -d --build
# rollback: git checkout <previous-tag> and run the same command
```

A restart is safe: a run that was in progress is marked `interrupted` (never silently re-run),
queued runs resume, and the queue file lives at `<data>/.work/run_queue.json`.

### What is not in this release yet

The admin page for concurrency and upload limits, sign-in, the noVNC gate, running as a
non-root user, and the scheduled backup script wait on T-204 and later units. Until the admin
page exists, set `AUTOTESTER_MAX_CONCURRENT_RUNS` in `server.env` and restart.

## Part B: Windows (development, or a Windows server)

Production is Ubuntu; this part covers developing on Windows and running the UI as a service
on a Windows machine without Docker.

Develop: install Python 3.11, `uv`, then `uv sync`, `uv run playwright install chromium`,
`uv run uvicorn autotester.ui.app:app --port 8000`. Run tests with `uv run pytest`.

Run as a service (pick one):

- **NSSM**: `nssm install AutoTester "C:\path\to\autoTesting\.venv\Scripts\uvicorn.exe"` with
  arguments `autotester.ui.app:app --host 127.0.0.1 --port 8000`, startup directory the repo
  folder, and `AutoTester` set to run as a normal user (a headed browser needs a desktop
  session, so tick "Interact with desktop" or log that user in). `nssm start AutoTester`.
- **Task Scheduler**: a task "At log on" running the same `uvicorn.exe` command with
  "Run only when user is logged on", restart on failure.

Settings go in the repo's `.env` (or system environment variables for the service):
`AUTOTESTER_ALLOWED_HOSTS=<host-or-ip>` and `AUTOTESTER_ALLOWED_ORIGINS=https://<host>`.
Without them every request from another machine gets 403.

Firewall: allow inbound TCP only for the port you serve on, from the networks that need it,
for example `New-NetFirewallRule -DisplayName AutoTester -Direction Inbound -Protocol TCP
-LocalPort 443 -Action Allow`. Do not open 6080 or 5900.

HTTPS: keep uvicorn on `127.0.0.1:8000` and put a reverse proxy in front (Caddy for Windows with
the same `Caddyfile` idea, or IIS with URL Rewrite and ARR), forwarding `Host` and raising the
body limit to `AUTOTESTER_MAX_UPLOAD_BYTES`. Back up the repo's `projects/`, `profiles/` and
`.env` the same way as Part A step 9.
