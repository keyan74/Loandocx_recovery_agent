# LoanDocX AI Recovery Agent

An autonomous incident agent for the LoanDocX website. It checks whether the public site is up, finds which layer failed, restarts the application only when the evidence supports it, and then verifies that the site is healthy again.

The model decides which checks to run. A Python controller executes those checks, blocks unsafe restarts, and writes a permanent incident record. A Gradio dashboard shows live status and past incidents.

## What it watches

LoanDocX is a Gradio app behind Nginx.

| Layer | What “healthy” means |
|---|---|
| DNS | `loandocx-agentai-demo.duckdns.org` resolves |
| Public HTTPS | The site returns HTTP 200 |
| Nginx | `nginx` is active |
| Application service | `loandocx.service` is active |
| Listening port | TCP `127.0.0.1:7860` is open |
| Direct backend | `http://127.0.0.1:7860/` returns HTTP 200 |

The usual outage this agent is built for: DNS is fine, Nginx is running, the public site returns HTTP 502, and `loandocx.service` is stopped. In that case the agent restarts the service and waits until the app is actually serving traffic.

## How a run works

1. `agent.py` asks the model (`gpt-5-mini` through the OpenAI Responses API) to diagnose the site.
2. The model requests tools such as `check_dns`, `check_https`, `check_nginx`, and `check_loandocx`.
3. The controller runs the matching Python function in `tools.py` and sends the real result back.
4. If the model asks for `restart_loandocx`, Python allows it only when all of these are already true:
   - DNS status is `OK`
   - HTTPS is `502`, `503`, or `504`
   - Nginx status is `RUNNING`
   - `loandocx.service` status is `NOT_RUNNING`
5. After a restart, the controller polls for up to 30 seconds. Recovery counts as successful only when the service is running, port 7860 is open, the local backend returns HTTP 200, and public HTTPS returns HTTP 200.
6. The run is saved to `incidents.json` as `HEALTHY`, `RECOVERED`, or `FAILED`.
7. `dashboard.py` reads that file and the live checks, and shows them in the browser.

The controller also limits a run to 6 model cycles, refuses a second restart in the same incident, and does not rerun a diagnostic whose result is already known unless the restart made that result stale.

If the restart does not restore the public site, the agent keeps investigating Nginx upstream config, the Nginx error log, and the `loandocx.service` journal. It does not keep restarting the service.

## Project layout

| File | Role |
|---|---|
| `agent.py` | Model loop, safety gate, recovery verification, incident writer |
| `tools.py` | DNS, HTTPS, Nginx, systemd, port, log, and restart checks |
| `monitor.py` | Small public-HTTPS check used on its own |
| `dashboard.py` | Gradio status and incident dashboard on port `7861` |
| `incidents.json` | Saved investigations |

## Tools the model can call

Diagnostics (read-only):

- `check_dns` — hostname resolution
- `check_https` — public HTTPS request
- `check_nginx` — `systemctl is-active nginx`
- `check_loandocx` — `systemctl is-active loandocx.service`
- `check_loandocx_port` — TCP connect to `127.0.0.1:7860`
- `check_backend` — HTTP GET of the app, bypassing Nginx
- `check_nginx_upstream` — `proxy_pass` and `upstream` lines from `nginx -T`
- `check_nginx_error_log` — last 100 lines of `/var/log/nginx/error.log`
- `check_loandocx_logs` — last 100 journal lines for `loandocx.service`

Recovery (changes server state):

- `restart_loandocx` — `sudo systemctl restart loandocx.service`

The prompt tells the model it may only describe checks the controller actually ran. Suggested shell commands for a human go under “optional human commands” and are marked as not executed by the agent.

## Incident record

Each saved incident includes:

- `incident_id` such as `INC-20261002-172421`
- `status`: `HEALTHY`, `RECOVERED`, or `FAILED`
- the recovery action, if any
- a written diagnosis from the model
- verification results for service, port, backend, and HTTPS
- the tool history with each result and whether it was a diagnostic, the recovery action, or a verification check

A recorded recovery looks like this:

1. DNS resolved.
2. Public HTTPS returned 502.
3. Nginx was running.
4. `loandocx.service` was inactive.
5. The controller restarted the service.
6. The service came up, port 7860 opened, the local app returned 200, and public HTTPS returned 200.

## Dashboard

`dashboard.py` is a Gradio app titled **LoanDocX AI Recovery Agent**. Refresh rebuilds four panels:

- overall healthy or unhealthy, plus DNS, HTTPS, Nginx, service, port, and backend
- the latest diagnosis
- a table of past incidents
- the tool history from the latest incident

It listens on `0.0.0.0:7861` with `root_path=/dashboard`, so it can sit behind Nginx at `/dashboard`.

## Run it

Python 3.10+ on the same host as Nginx and `loandocx.service`.

```bash
pip install openai python-dotenv requests gradio urllib3
```

`agent.py` loads `OPENAI_API_KEY` from `/home/ec2-user/loandocx/.env`. The process needs permission to query systemd and, for recovery and log reads, passwordless `sudo` for `systemctl restart loandocx.service`, `tail` of the Nginx error log, `journalctl`, and `nginx -T`.

```bash
# one diagnostic pass, no model
python tools.py

# public HTTPS only
python monitor.py

# full diagnose-and-recover run
python agent.py

# live dashboard
python dashboard.py
```



point the agent at another app.
