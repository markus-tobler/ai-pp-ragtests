#!/usr/bin/env python3
"""Run Copilot Studio evaluations for every MultiEURLEX agent and collect results.

Drives the Power Platform "maker evaluation" API (PPAPI) for each agent listed
in agent-instructions/README.md:

  a) CHECK  - GET .../testsets for every agent. Each agent must have *exactly
              one* test set. Abort (no runs started) if any agent has zero or
              more than one. Publishing is intentionally skipped: evaluations
              run against the DRAFT (unpublished) bot.
  b) RUN    - POST .../testsets/{id}/run for every agent (runOnPublishedBot=false),
              passing the MCS connection id so authenticated knowledge sources
              and Dataverse MCP tools actually execute. Then poll each run until
              it reaches a terminal state.
  c) COLLECT- GET .../testruns/{runId} for every agent and write the raw run +
              per-case results plus a roll-up summary into
              data/eval/results/run_<UTC-timestamp>/ for further analysis.

API surface (api-version 2024-10-01), base per agent:
  https://api.powerplatform.com/copilotstudio/environments/{envId}/bots/{botId}/api/makerevaluation
    GET  /testsets                  -> list test sets
    POST /testsets/{id}/run         -> start a run  (body: runOnPublishedBot, evaluationRunName, mcsConnectionId)
    GET  /testruns/{runId}          -> run status + testCasesResults

Auth: MSAL public-client device-code/interactive flow using MCP_CLIENT_ID from
.env, scope https://api.powerplatform.com/.default. The App Registration needs
CopilotStudio.MakerOperations.Read and CopilotStudio.Copilots.Invoke. Tokens are
cached in .token_cache.bin (gitignored).

Config (.env in repo root):
  EVAL_CLIENT_ID      required  App Registration client id with Power Platform API
                                delegated perms (see docs/EVAL_APP_REGISTRATION.md).
                                Falls back to MCP_CLIENT_ID, but the Dataverse CLI
                                client lacks api.powerplatform.com access (AADSTS650057).
  DATAVERSE_URL       required  e.g. https://mto-training-management.crm.dynamics.com
  TENANT_ID           required
  ENVIRONMENT_ID      optional  Power Platform environment GUID. Set this to avoid a
                                SECOND interactive login for discovery.
  MCS_CONNECTION_ID   optional  Microsoft Copilot Studio connection id (prompted if absent)

Usage:
  python scripts/run_agent_evals.py            # full check -> run -> collect
  python scripts/run_agent_evals.py --check-only
  python scripts/run_agent_evals.py --anonymous   # no connection id (tools/knowledge skipped)
"""

from __future__ import annotations

import argparse
import atexit
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import msal
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
README_PATH = REPO_ROOT / "agent-instructions" / "README.md"
RESULTS_ROOT = REPO_ROOT / "data" / "eval" / "results"
TOKEN_CACHE_PATH = REPO_ROOT / ".token_cache.bin"

PP_API_SCOPE = "https://api.powerplatform.com/.default"
PP_API_VERSION = "2024-10-01"
# Environment-management API: maps the Dataverse instance URL -> Power Platform
# environment id, using the SAME PP token (no second login, no discovery perm).
PP_ENV_MGMT_URL = "https://api.powerplatform.com/environmentmanagement/environments"
PP_ENV_MGMT_VERSION = "2022-03-01-preview"

POLL_INTERVAL_S = 20
POLL_TIMEOUT_S = 60 * 60  # 1 hour hard cap across all runs
TERMINAL_STATES = {"Completed", "Failed", "Abandoned", "Cancelled", "Error"}

CONNECTION_GUIDE = """
An MCS connection id is required so the eval can call authenticated knowledge
sources and Dataverse MCP tools as you. Without it the run is anonymous and
those tools/knowledge are NOT used (results are meaningless for the mcp /
semantic / hybrid / knowledge agents).

How to get one:
  1. Go to https://make.powerautomate.com
  2. Open 'Connections' from the side menu
  3. Select the relevant 'Microsoft Copilot Studio' connection
  4. Copy the GUID from the URL (the segment after /connections/)

Set it as MCS_CONNECTION_ID in .env to avoid this prompt next time, or paste it
below. Leave blank to run anonymously.
""".strip()


# ---------------------------------------------------------------------------
# .env loading (no external dotenv dependency)
# ---------------------------------------------------------------------------

def load_env() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


# ---------------------------------------------------------------------------
# Agent discovery — parse the "## Agents" table in the README
# ---------------------------------------------------------------------------

def parse_agents() -> list[dict]:
    """Return [{name, bot_id, instruction_file, environment}] from README table."""
    if not README_PATH.exists():
        die(f"README not found: {README_PATH}")
    text = README_PATH.read_text(encoding="utf-8")

    # Isolate the section starting at '## Agents'
    section = text.split("## Agents", 1)
    if len(section) < 2:
        die("Could not find '## Agents' section in README.")
    body = section[1]

    agents: list[dict] = []
    for row in body.splitlines():
        row = row.strip()
        if not row.startswith("|"):
            continue
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) < 2:
            continue
        # skip header and separator rows
        if cells[0].lower() == "agent" or set(cells[0]) <= {"-", ":"}:
            continue
        bot_id = cells[1].strip().strip("`")
        if not re.fullmatch(r"[0-9a-fA-F-]{36}", bot_id):
            continue
        agents.append({
            "name": cells[0],
            "bot_id": bot_id,
            "instruction_file": cells[2] if len(cells) > 2 else "",
            "environment": cells[3] if len(cells) > 3 else "",
        })
    if not agents:
        die("No agents parsed from README '## Agents' table.")
    return agents


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _build_msal_app(client_id: str, tenant_id: str) -> msal.PublicClientApplication:
    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE_PATH.exists():
        cache.deserialize(TOKEN_CACHE_PATH.read_text(encoding="utf-8"))

    @atexit.register
    def _persist() -> None:
        if cache.has_state_changed:
            TOKEN_CACHE_PATH.write_text(cache.serialize(), encoding="utf-8")

    return msal.PublicClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=cache,
    )


def acquire_token(app: msal.PublicClientApplication, scope: str) -> str | None:
    scopes = [scope]
    accounts = app.get_accounts()
    if accounts:
        res = app.acquire_token_silent(scopes, account=accounts[0])
        if res and "access_token" in res:
            return res["access_token"]

    flow = app.initiate_device_flow(scopes=scopes)
    if "user_code" not in flow:
        die(f"Failed to start device flow: {flow.get('error_description', flow)}")
    print(f"\n>>> {flow['message']}\n", flush=True)
    res = app.acquire_token_by_device_flow(flow)
    if "access_token" not in res:
        # for optional scopes (e.g. discovery) caller decides how fatal this is
        log(f"Token acquisition failed for {scope}: {res.get('error_description', res.get('error'))}")
        return None
    return res["access_token"]


# ---------------------------------------------------------------------------
# Environment id resolution
# ---------------------------------------------------------------------------

def list_environments(token: str) -> list[dict]:
    """Return [{env_id, instance_url, display_name}] from the PP env-mgmt API."""
    url = f"{PP_ENV_MGMT_URL}?api-version={PP_ENV_MGMT_VERSION}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}",
                                   "Accept": "application/json"}, timeout=30)
    if not r.ok:
        die(f"Could not list environments (HTTP {r.status_code}): {r.text[:300]}")
    out = []
    for env in r.json().get("value", []):
        props = env.get("properties", {})
        linked = props.get("linkedEnvironmentMetadata", {}) or {}
        # env id is the bare GUID in 'name' (sometimes 'id' is "/environments/<guid>")
        env_id = env.get("name") or (env.get("id", "").rsplit("/", 1)[-1])
        out.append({
            "env_id": env_id,
            "instance_url": (linked.get("instanceUrl") or linked.get("instanceApiUrl") or "").rstrip("/"),
            "display_name": props.get("displayName") or env.get("name", ""),
        })
    return out


def resolve_environment_id(token: str, dataverse_url: str) -> str:
    env_id = os.environ.get("ENVIRONMENT_ID", "").strip()
    if env_id:
        return env_id

    target_host = urlparse(dataverse_url).hostname or ""
    log("ENVIRONMENT_ID not set; resolving via Power Platform environment-management API...")
    for env in list_environments(token):
        if urlparse(env["instance_url"]).hostname == target_host:
            log(f"Resolved ENVIRONMENT_ID={env['env_id']} ({env['display_name']}) "
                f"for {env['instance_url']}")
            return env["env_id"]

    print(
        "\nCould not match an environment to DATAVERSE_URL automatically.\n"
        "Run 'python3 scripts/run_agent_evals.py --list-environments' to see ids,\n"
        "or set ENVIRONMENT_ID in .env (Power Platform Admin Center >> Environments\n"
        ">> your environment >> 'Environment ID').",
        flush=True,
    )
    env_id = input("Environment ID: ").strip()
    if not env_id:
        die("Environment ID is required.")
    return env_id


# ---------------------------------------------------------------------------
# Connection id
# ---------------------------------------------------------------------------

def resolve_connection_id(anonymous: bool) -> str | None:
    if anonymous:
        return None
    conn = os.environ.get("MCS_CONNECTION_ID", "").strip()
    if conn:
        return conn
    print("\n" + CONNECTION_GUIDE + "\n", flush=True)
    conn = input("MCS_CONNECTION_ID (blank = anonymous): ").strip()
    return conn or None


# ---------------------------------------------------------------------------
# PPAPI client
# ---------------------------------------------------------------------------

class EvalApi:
    def __init__(self, token: str, environment_id: str):
        self.token = token
        self.environment_id = environment_id
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _base(self, bot_id: str) -> str:
        return (f"https://api.powerplatform.com/copilotstudio/environments/"
                f"{self.environment_id}/bots/{bot_id}/api/makerevaluation")

    def _url(self, bot_id: str, path: str) -> str:
        sep = "&" if "?" in path else "?"
        return f"{self._base(bot_id)}{path}{sep}api-version={PP_API_VERSION}"

    def _request(self, method: str, url: str, body: dict | None = None) -> dict | None:
        resp = self.session.request(method, url, json=body, timeout=60)
        if resp.status_code in (401, 403):
            die(f"Auth failed (HTTP {resp.status_code}). Token may lack "
                f"CopilotStudio.MakerOperations.Read / Copilots.Invoke.\n{resp.text[:300]}")
        if resp.status_code == 409:
            raise ApiConflict(resp.text[:300])
        if resp.status_code == 429:
            die(f"Rate limited (HTTP 429): max 20 eval runs per bot per 24h.\n{resp.text[:300]}")
        if not resp.ok:
            die(f"HTTP {resp.status_code} {method} {url}\n{resp.text[:500]}")
        if not resp.text.strip():
            return None
        return resp.json()

    def list_testsets(self, bot_id: str) -> list[dict]:
        data = self._request("GET", self._url(bot_id, "/testsets"))
        return (data or {}).get("value", []) if data else []

    def start_run(self, bot_id: str, testset_id: str, run_name: str,
                  connection_id: str | None, published: bool = False) -> dict:
        body = {"runOnPublishedBot": published, "evaluationRunName": run_name}
        if connection_id:
            body["mcsConnectionId"] = connection_id
        return self._request("POST", self._url(bot_id, f"/testsets/{testset_id}/run"), body) or {}

    def get_run(self, bot_id: str, run_id: str) -> dict:
        return self._request("GET", self._url(bot_id, f"/testruns/{run_id}")) or {}


class ApiConflict(Exception):
    pass


# ---------------------------------------------------------------------------
# Result roll-up
# ---------------------------------------------------------------------------

def summarize_run(run: dict) -> dict:
    """Best-effort pass/fail roll-up that tolerates schema variation."""
    cases = run.get("testCasesResults") or run.get("testCases") or []
    total = len(cases)
    errors = 0
    metric_tally: dict[str, dict[str, int]] = {}

    for case in cases:
        status = (case.get("status") or case.get("executionState") or "").lower()
        if "error" in status or "fail" == status:
            errors += 1
        metrics = case.get("metricResults") or case.get("metrics") or case.get("metricsResults") or []
        if isinstance(metrics, dict):
            metrics = [dict(metricName=k, **(v if isinstance(v, dict) else {"result": v}))
                       for k, v in metrics.items()]
        for m in metrics:
            name = m.get("metricName") or m.get("name") or "metric"
            result = str(m.get("result") or m.get("status") or m.get("verdict") or "").strip() or "Unknown"
            tally = metric_tally.setdefault(name, {})
            tally[result] = tally.get(result, 0) + 1

    return {
        "totalTestCases": run.get("totalTestCases", total),
        "testCasesProcessed": run.get("testCasesProcessed", total),
        "errors": errors,
        "metrics": metric_tally,
    }


def write_results(out_dir: Path, agents_state: list[dict]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    for st in agents_state:
        slug = slugify(st["agent"]["name"])
        run = st.get("run") or {}
        (out_dir / f"{slug}.json").write_text(
            json.dumps({"agent": st["agent"], "runId": st.get("run_id"),
                        "state": st.get("state"), "run": run}, indent=2),
            encoding="utf-8",
        )
        summ = summarize_run(run) if run else {}
        # flatten metric pass-rates into a readable string
        metric_str = "; ".join(
            f"{name}:" + ",".join(f"{k}={v}" for k, v in sorted(verdicts.items()))
            for name, verdicts in (summ.get("metrics") or {}).items()
        )
        summary_rows.append({
            "agent": st["agent"]["name"],
            "bot_id": st["agent"]["bot_id"],
            "instruction_file": st["agent"].get("instruction_file", ""),
            "run_id": st.get("run_id") or "",
            "state": st.get("state") or "",
            "total": summ.get("totalTestCases", ""),
            "processed": summ.get("testCasesProcessed", ""),
            "errors": summ.get("errors", ""),
            "metrics": metric_str,
        })

    # summary.csv
    fields = ["agent", "bot_id", "instruction_file", "run_id", "state",
              "total", "processed", "errors", "metrics"]
    with (out_dir / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(summary_rows)

    # summary.json (machine-readable, includes per-metric tallies)
    (out_dir / "summary.json").write_text(
        json.dumps({
            "generatedUtc": datetime.now(timezone.utc).isoformat(),
            "agents": [{
                "agent": st["agent"]["name"],
                "bot_id": st["agent"]["bot_id"],
                "run_id": st.get("run_id"),
                "state": st.get("state"),
                "summary": summarize_run(st["run"]) if st.get("run") else None,
            } for st in agents_state],
        }, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Orchestration phases
# ---------------------------------------------------------------------------

def phase_check(api: EvalApi, agents: list[dict]) -> list[dict]:
    """Require exactly one test set per agent. Abort if any violate."""
    log("Phase A: checking test sets (require exactly one per agent)...")
    state = []
    problems = []
    for agent in agents:
        testsets = api.list_testsets(agent["bot_id"])
        names = [ts.get("displayName") for ts in testsets]
        log(f"  {agent['name']}: {len(testsets)} test set(s) {names}")
        if len(testsets) != 1:
            problems.append(f"  {agent['name']} ({agent['bot_id']}): "
                            f"found {len(testsets)} test sets {names} (need exactly 1)")
        state.append({"agent": agent,
                      "testset": testsets[0] if len(testsets) == 1 else None})
    if problems:
        die("Test set check failed (no runs started):\n" + "\n".join(problems))
    log("All agents have exactly one test set. OK.")
    return state


def phase_run(api: EvalApi, state: list[dict], run_name: str,
              connection_id: str | None) -> None:
    log(f"Phase B: starting eval runs (draft bot, anonymous={connection_id is None})...")
    for st in state:
        agent, testset = st["agent"], st["testset"]
        try:
            res = api.start_run(agent["bot_id"], testset["id"], run_name, connection_id)
        except ApiConflict as e:
            die(f"{agent['name']}: a run is already in progress for this bot "
                f"(HTTP 409). Wait for it to finish, then retry.\n{e}")
        st["run_id"] = res.get("runId") or res.get("id")
        st["state"] = res.get("state") or res.get("executionState")
        if not st["run_id"]:
            die(f"{agent['name']}: start-run returned no runId: {res}")
        log(f"  {agent['name']}: runId={st['run_id']} state={st['state']}")


def phase_poll(api: EvalApi, state: list[dict]) -> None:
    log("Phase B: polling runs until terminal state...")
    deadline = time.time() + POLL_TIMEOUT_S
    pending = {id(st): st for st in state}
    while pending and time.time() < deadline:
        for key in list(pending):
            st = pending[key]
            agent = st["agent"]
            run = api.get_run(agent["bot_id"], st["run_id"])
            st["run"] = run
            st["state"] = run.get("state") or run.get("executionState") or st.get("state")
            done = run.get("testCasesProcessed", 0)
            total = run.get("totalTestCases", "?")
            log(f"  {agent['name']}: {st['state']} ({done}/{total})")
            if st["state"] in TERMINAL_STATES:
                del pending[key]
        if pending:
            time.sleep(POLL_INTERVAL_S)
    if pending:
        for st in pending.values():
            log(f"  WARNING: {st['agent']['name']} did not finish before timeout "
                f"(state={st.get('state')}).")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_probe(token: str, agents: list[dict], environment_id: str) -> None:
    """Hit a control route + the copilotstudio eval route across api-versions."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    bot_id = agents[0]["bot_id"]
    cs_base = (f"https://api.powerplatform.com/copilotstudio/environments/"
               f"{environment_id}/bots/{bot_id}/api/makerevaluation/testsets")
    probes = [
        ("env-mgmt list (control)",
         f"{PP_ENV_MGMT_URL}?api-version={PP_ENV_MGMT_VERSION}"),
        ("copilotstudio testsets v2024-10-01", f"{cs_base}?api-version=2024-10-01"),
        ("copilotstudio testsets v2023-06-01", f"{cs_base}?api-version=2023-06-01"),
        ("copilotstudio testsets v2022-03-01-preview", f"{cs_base}?api-version=2022-03-01-preview"),
        ("copilotstudio testsets (no version)", cs_base),
    ]
    print(f"Environment: {environment_id}\nBot: {bot_id}\n")
    for label, url in probes:
        try:
            r = requests.get(url, headers=headers, timeout=30)
            body = r.text.strip().replace("\n", " ")
            code = ""
            try:
                code = r.json().get("code", "")
            except Exception:
                pass
            print(f"[{r.status_code:>3}] {code:<16} {label}")
            if not r.ok:
                print(f"        {body[:180]}")
        except requests.RequestException as e:
            print(f"[ERR]  {label}: {e}")


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Run Copilot Studio evals for all MultiEURLEX agents.")
    ap.add_argument("--check-only", action="store_true",
                    help="Only verify each agent has exactly one test set; do not run.")
    ap.add_argument("--anonymous", action="store_true",
                    help="Run without a connection id (tools/knowledge skipped).")
    ap.add_argument("--run-name", default=None, help="Display name for the eval runs.")
    ap.add_argument("--list-environments", action="store_true",
                    help="List environments visible to this token (id + Dataverse URL) and exit.")
    ap.add_argument("--probe", action="store_true",
                    help="Diagnose: hit env-mgmt (control) + copilotstudio eval routes across "
                         "api-versions, print raw status, and exit.")
    args = ap.parse_args()

    load_env()
    dataverse_url = os.environ.get("DATAVERSE_URL", "").strip()
    tenant_id = os.environ.get("TENANT_ID", "").strip()
    client_id = os.environ.get("EVAL_CLIENT_ID", "").strip() or os.environ.get("MCP_CLIENT_ID", "").strip()
    for name, val in [("DATAVERSE_URL", dataverse_url), ("TENANT_ID", tenant_id),
                      ("EVAL_CLIENT_ID (or MCP_CLIENT_ID)", client_id)]:
        if not val:
            die(f"{name} missing from .env")
    if os.environ.get("EVAL_CLIENT_ID", "").strip() == "" and client_id:
        log("WARNING: EVAL_CLIENT_ID not set; falling back to MCP_CLIENT_ID. If you hit "
            "AADSTS650057 (Invalid resource), that client lacks Power Platform API access "
            "- create a dedicated app per docs/EVAL_APP_REGISTRATION.md.")

    agents = parse_agents()
    log(f"Discovered {len(agents)} agents from {README_PATH.relative_to(REPO_ROOT)}:")
    for a in agents:
        log(f"  - {a['name']} ({a['bot_id']})")

    app = _build_msal_app(client_id, tenant_id)
    token = acquire_token(app, PP_API_SCOPE)
    if not token:
        die("Could not acquire a Power Platform API token.")

    if args.list_environments:
        print(f"{'ENVIRONMENT ID':<38} {'DATAVERSE URL':<55} DISPLAY NAME")
        for env in list_environments(token):
            print(f"{env['env_id']:<38} {env['instance_url']:<55} {env['display_name']}")
        return

    if args.probe:
        run_probe(token, agents, resolve_environment_id(token, dataverse_url))
        return

    environment_id = resolve_environment_id(token, dataverse_url)
    log(f"Using environment id: {environment_id}")
    api = EvalApi(token, environment_id)

    # Phase A — check (always)
    state = phase_check(api, agents)
    if args.check_only:
        log("Check-only mode: all agents OK. Exiting without running.")
        return

    connection_id = resolve_connection_id(args.anonymous)
    if connection_id is None:
        log("WARNING: running anonymously — authenticated tools/knowledge will NOT execute.")

    run_name = args.run_name or f"Batch eval {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}"

    # Phase B — run + poll
    phase_run(api, state, run_name, connection_id)
    phase_poll(api, state)

    # Phase C — collect
    stamp = datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    out_dir = RESULTS_ROOT / stamp
    write_results(out_dir, state)
    log(f"Phase C: results written to {out_dir.relative_to(REPO_ROOT)}")

    # Final console summary
    print("\n=== Evaluation summary ===")
    for st in state:
        print(f"  {st['agent']['name']:<40} {st.get('state','?'):<12} runId={st.get('run_id')}")
    print(f"\nFull results: {out_dir.relative_to(REPO_ROOT)}/  (summary.csv, summary.json, <agent>.json)")


if __name__ == "__main__":
    main()
