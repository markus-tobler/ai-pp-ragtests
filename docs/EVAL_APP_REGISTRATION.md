# App Registration for `run_agent_evals.py`

`scripts/run_agent_evals.py` calls the **Power Platform "maker evaluation" API**
(`https://api.powerplatform.com/...`) to run Copilot Studio evaluations against
each agent's draft bot. That needs an Entra ID (Azure AD) **App Registration**
whose delegated permissions include the Power Platform API.

The Dataverse CLI client already in `.env` as `MCP_CLIENT_ID`
(`0c412cc3-0dd6-449b-987f-05b053db9457`) does **not** work — it is only
consented for Dataverse + Power Apps, so the eval token request fails with:

```
AADSTS650057: Invalid resource. ... Resource value from request:
https://api.powerplatform.com. ... List of valid resources from app
registration: 00000007-... , 00000015-...
```

Create your own app registration as below, then put its client id in `.env` as
`EVAL_CLIENT_ID`.

---

## What the script needs from the app

| Requirement | Value | Why |
|---|---|---|
| Account type | Single tenant | Only used in your tenant |
| Public client flows | **Enabled** | Script uses the **device code** flow (no client secret) |
| Delegated API permission | `CopilotStudio.MakerOperations.Read` | List test sets, start/read eval runs |
| Delegated API permission | `CopilotStudio.Copilots.Invoke` | Invoke the bot during the eval |

Environment-id auto-resolution (Dataverse URL -> environment id) uses the Power
Platform **environment-management** API under the same `api.powerplatform.com`
resource, so no extra Dynamics CRM permission is needed. If that listing is
blocked in your tenant, set `ENVIRONMENT_ID` in `.env` and it is skipped.

The Power Platform API resource app id is
`8578e004-a5c6-46e7-913e-12f58912df43` ("Power Platform API"). The two scopes
above live under it.

> The signed-in user also needs **maker access** to the environment / agents.
> The app registration grants the *API surface*; the *user* is still
> authorizing as themselves (delegated), so they must be able to edit the agents
> in Copilot Studio.

---

## Step-by-step (Azure Portal)

1. **Entra ID > App registrations > New registration**
   - Name: e.g. `multieurlex-eval-runner`
   - Supported account types: **Accounts in this organizational directory only**
   - Redirect URI: leave blank (device code needs none). Click **Register**.
   - Copy the **Application (client) ID** and **Directory (tenant) ID**.

2. **Authentication > Advanced settings > Allow public client flows → Yes**, Save.
   (Device code flow is a public-client flow; without this you get
   `AADSTS7000218`.)

3. **API permissions > Add a permission**
   - Pick **Power Platform API**.
     - If it is not listed: it may not be provisioned in the tenant yet. A
       tenant admin can register it once with
       `New-AzureADServicePrincipal -AppId "8578e004-a5c6-46e7-913e-12f58912df43"`
       (AzureAD module) or
       `az ad sp create --id 8578e004-a5c6-46e7-913e-12f58912df43`. Then retry.
   - **Delegated permissions** > add:
     - `CopilotStudio.MakerOperations.Read`
     - `CopilotStudio.Copilots.Invoke`
   - Click **Grant admin consent for <tenant>** (or have an admin do it).
     Without consent the first login shows a consent prompt; admin consent
     avoids per-user prompts.

4. Done. No client secret / certificate is required (device code is interactive).

---

## Wire it into `.env`

Add (or update) these keys in the repo-root `.env`:

```dotenv
# App registration with Power Platform API delegated perms (this doc)
EVAL_CLIENT_ID=<your new Application (client) ID>

# Set this to avoid a SECOND interactive login (Global Discovery).
# Power Platform Admin Center > Environments > <env> > "Environment ID".
ENVIRONMENT_ID=<environment GUID>

# Microsoft Copilot Studio connection id, so authenticated knowledge / MCP
# tools run as you during the eval. make.powerautomate.com > Connections >
# Microsoft Copilot Studio > GUID after /connections/ in the URL.
MCS_CONNECTION_ID=<connection GUID>
```

`TENANT_ID` and `DATAVERSE_URL` are already present from the existing setup.

---

## Login behavior / minimizing prompts

- The script uses MSAL **device code**: it prints a URL + code; open it, sign in,
  approve. Tokens are cached in `.token_cache.bin` (gitignored) and reused
  silently on later runs until they expire.
- **One login.** A single Power Platform API token covers both the evaluation
  calls and the environment-id lookup, so there is no second prompt even when
  `ENVIRONMENT_ID` is unset.
- If you ever switch the client id, delete `.token_cache.bin` to force a clean
  login.

---

## Verify

```bash
python3 scripts/run_agent_evals.py --check-only
```

Expected: one device-code login, then a list of the 5 agents each reporting
"1 test set". If you see `AADSTS650057`, `EVAL_CLIENT_ID` is still pointing at an
app without Power Platform API permission.
