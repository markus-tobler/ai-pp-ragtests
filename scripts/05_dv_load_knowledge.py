"""Load each MultiEURLEX document as a separate Copilot Studio knowledge file.

Reads data/processed/multieurlex_selected_300.csv and, for every row (one EU
legal document), creates a `botcomponent` of type "Bot File Attachment" (14) on
the target agent and uploads the document as a Markdown file to that component's
`filedata` file column. Copilot Studio treats type-14 file attachments as agent
knowledge automatically (no separate Knowledge Source record is required), so
after publishing the agent each document becomes individually searchable.

This is the Dataverse Web API equivalent of the Power Automate flow in
https://www.matthewdevaney.com/how-to-add-copilot-studio-knowledge-files-using-power-automate/
(List bots -> Add botcomponent row -> Upload to filedata -> PvaPublish).

Per-document file format (decided): Markdown with a YAML frontmatter block of
all metadata columns, followed by the full document_text as the body. The
uploaded file is named `<celex_id>.md` (extension kept so Copilot detects the
Markdown type). The botcomponent `name` is the bare CELEX id, and its
`description` holds the document title plus compact metadata.

Target agent (bot):
  name   : MultiEURLEX Classic DV Knowledge
  botid  : b6a6468d-632d-49df-93a1-aa1a9afbf4d6
  schema : new_multieurlexclassicdvknowledge

Idempotency / rerun:
  Existing type-14 components on the bot are listed once up front. A row whose
  target filename already exists is skipped, unless --overwrite is given, in
  which case the existing component is deleted and recreated. If a file upload
  fails after its component was created, the empty component is rolled back
  (deleted) so a plain rerun is a clean resume: missing docs get created,
  already-loaded ones are skipped, no empty orphans are left behind.

Usage:
    python scripts/05_dv_load_knowledge.py                 # DRY RUN — preview only, no write
    python scripts/05_dv_load_knowledge.py --execute       # create + upload all files, then publish
    python scripts/05_dv_load_knowledge.py --execute --limit 5      # smoke test (first 5)
    python scripts/05_dv_load_knowledge.py --execute --overwrite    # replace existing files
    python scripts/05_dv_load_knowledge.py --execute --clean        # wipe all knowledge first, then load fresh
    python scripts/05_dv_load_knowledge.py --execute --no-publish   # skip PvaPublish
"""
import argparse
import csv
import json
import os
import random
import re
import string
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from auth import get_token, get_plugin_headers, load_env

# ── Target agent ────────────────────────────────────────────────────────────
BOT_ID = "b6a6468d-632d-49df-93a1-aa1a9afbf4d6"
BOT_SCHEMA = "new_multieurlexclassicdvknowledge"

DATA_FILE = Path("data/processed/multieurlex_selected_300.csv")
API_VERSION = "v9.2"
COMPONENTTYPE_FILE_ATTACHMENT = 14

# Column holding the document body. Everything else becomes frontmatter.
BODY_COLUMN = "document_text"
KEY_COLUMN = "celex_id"

# Dataverse field size limits (from botcomponent schema).
NAME_MAXLEN = 500          # name NVARCHAR(500)
SCHEMANAME_MAXLEN = 100    # schemaname NVARCHAR(100)
DESCRIPTION_MAXLEN = 2000  # description is MULTILINE TEXT; cap for tidiness

# Metadata columns surfaced in the component description (title first, then
# compact key/value context). Order matters; missing/empty values are skipped.
DESCRIPTION_COLUMNS = [
    "policy_domain", "document_type", "year", "year_band", "language",
    "length_level", "legal_actor_type", "applicable_role", "word_count",
]

# csv field size limit — document_text can be large.
csv.field_size_limit(10 * 1024 * 1024)

# HTTP behaviour: per-request socket timeout + retry on throttling / transient 5xx.
# Without a timeout, urllib blocks forever on a stuck socket or a silent throttle.
HTTP_TIMEOUT = 60          # seconds per request
HTTP_MAX_RETRIES = 5       # attempts on 429 / 502 / 503 / 504 / timeout
HTTP_RETRY_STATUSES = {429, 502, 503, 504}


# ── HTTP helpers (raw Dataverse Web API via urllib) ─────────────────────────
def _api_base():
    url = os.environ.get("DATAVERSE_URL", "").rstrip("/")
    if not url:
        print("ERROR: DATAVERSE_URL not set in .env", flush=True)
        sys.exit(1)
    return f"{url}/api/data/{API_VERSION}"


def _request(method, url, token, *, data=None, extra_headers=None):
    """Issue a Web API request. Returns (status, response_headers, body_bytes)."""
    headers = get_plugin_headers("unknown", token)
    headers["Accept"] = "application/json"
    headers["OData-MaxVersion"] = "4.0"
    headers["OData-Version"] = "4.0"
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    last_err = None
    for attempt in range(1, HTTP_MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code in HTTP_RETRY_STATUSES and attempt < HTTP_MAX_RETRIES:
                # Honor Retry-After when present; else exponential backoff.
                wait = float(e.headers.get("Retry-After") or 0) or min(2 ** attempt, 30)
                print(f"    throttled HTTP {e.code}, retry {attempt}/{HTTP_MAX_RETRIES} in {wait:.0f}s", flush=True)
                time.sleep(wait)
                last_err = RuntimeError(f"{method} {url} -> HTTP {e.code}: {body}")
                continue
            raise RuntimeError(f"{method} {url} -> HTTP {e.code}: {body}") from None
        except (urllib.error.URLError, TimeoutError) as e:
            # Socket timeout / connection reset — transient, retry with backoff.
            if attempt < HTTP_MAX_RETRIES:
                wait = min(2 ** attempt, 30)
                print(f"    network error ({e}), retry {attempt}/{HTTP_MAX_RETRIES} in {wait:.0f}s", flush=True)
                time.sleep(wait)
                last_err = RuntimeError(f"{method} {url} -> {e}")
                continue
            raise RuntimeError(f"{method} {url} -> {e}") from None
    raise last_err


def list_existing_files(token):
    """Return {name: botcomponentid} for existing type-14 components on the bot."""
    params = urllib.parse.urlencode({
        "$select": "botcomponentid,name",
        "$filter": (f"_parentbotid_value eq {BOT_ID} and "
                    f"componenttype eq {COMPONENTTYPE_FILE_ATTACHMENT}"),
    })
    _, _, body = _request("GET", f"{_api_base()}/botcomponents?{params}", token)
    rows = json.loads(body).get("value", [])
    return {r["name"]: r["botcomponentid"] for r in rows}


def create_component(token, name, description, schemaname):
    """Create the botcomponent row. Returns the new botcomponentid."""
    payload = {
        "componenttype": COMPONENTTYPE_FILE_ATTACHMENT,
        "name": name,
        "schemaname": schemaname,
        "description": description,
        "parentbotid@odata.bind": f"/bots({BOT_ID})",
    }
    _, headers, body = _request(
        "POST",
        f"{_api_base()}/botcomponents",
        token,
        data=json.dumps(payload).encode("utf-8"),
        extra_headers={"Content-Type": "application/json", "Prefer": "return=representation"},
    )
    # With return=representation the id is in the JSON body; otherwise it is in
    # the OData-EntityId header (botcomponents(<guid>)).
    if body:
        try:
            cid = json.loads(body).get("botcomponentid")
            if cid:
                return cid
        except json.JSONDecodeError:
            pass
    entity_id = headers.get("OData-EntityId") or headers.get("odata-entityid", "")
    m = re.search(r"botcomponents\(([0-9a-fA-F-]{36})\)", entity_id)
    if not m:
        raise RuntimeError(f"Could not parse new botcomponentid (body={body[:200]!r}, header={entity_id!r})")
    return m.group(1)


def upload_filedata(token, component_id, filename, content_bytes):
    """Upload bytes to the filedata file column (single-request PATCH, <128MB)."""
    url = f"{_api_base()}/botcomponents({component_id})/filedata"
    _request(
        "PATCH",
        url,
        token,
        data=content_bytes,
        extra_headers={
            "Content-Type": "application/octet-stream",
            "x-ms-file-name": filename,
        },
    )


def delete_component(token, component_id):
    _request("DELETE", f"{_api_base()}/botcomponents({component_id})", token)


def purge_all_files(token, existing):
    """Delete every existing type-14 component on the bot in one sweep.

    Used by --clean to wipe the agent's file knowledge before a fresh load,
    instead of reconciling row-by-row. Returns the number deleted.
    """
    total = len(existing)
    deleted = 0
    for name, cid in existing.items():
        delete_component(token, cid)
        deleted += 1
        print(f"  purged {deleted}/{total}: {name}", flush=True)
    return deleted


def publish_bot(token):
    """Run the PvaPublish bound action so the new knowledge goes live."""
    url = f"{_api_base()}/bots({BOT_ID})/Microsoft.Dynamics.CRM.PvaPublish"
    _request("POST", url, token, data=b"{}",
             extra_headers={"Content-Type": "application/json"})


# ── Content building ────────────────────────────────────────────────────────
def build_markdown(row):
    """Render one CSV row as Markdown: YAML frontmatter (metadata) + text body."""
    lines = ["---"]
    for col, val in row.items():
        if col == BODY_COLUMN:
            continue
        val = "" if val is None else str(val)
        # json.dumps yields a valid YAML double-quoted scalar (escapes quotes,
        # colons, embedded newlines) — keeps frontmatter parseable for any value.
        lines.append(f"{col}: {json.dumps(val)}")
    lines.append("---")
    lines.append("")
    lines.append((row.get(BODY_COLUMN) or "").strip())
    lines.append("")
    return "\n".join(lines)


def build_description(row):
    """Title + compact metadata for the component description (<= DESCRIPTION_MAXLEN)."""
    title = (row.get("title") or "").strip()
    celex = (row.get(KEY_COLUMN) or "").strip()
    parts = [p for p in (title, f"CELEX {celex}") if p.strip()]
    for col in DESCRIPTION_COLUMNS:
        val = (row.get(col) or "").strip()
        if val:
            parts.append(f"{col}: {val}")
    desc = " | ".join(parts)
    if len(desc) > DESCRIPTION_MAXLEN:
        desc = desc[: DESCRIPTION_MAXLEN - 1].rstrip() + "…"
    return desc


def _schemaname(celex):
    """{bot}.file.{sanitized}_{rand3} — sanitized + length-capped to stay valid."""
    token = re.sub(r"[^A-Za-z0-9]", "", celex)
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=3))
    base = f"{BOT_SCHEMA}.file."
    token = token[: max(1, SCHEMANAME_MAXLEN - len(base) - 4)]  # 4 = "_xxx"
    return f"{base}{token}_{suffix}"


def load_rows(path, limit=None):
    """Parse CSV (quoted fields with embedded newlines) into a list of dict rows."""
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for src in csv.DictReader(f):
            celex = (src.get(KEY_COLUMN) or "").strip()
            if not celex:
                print("  ! skipping row with missing celex_id", flush=True)
                continue
            rows.append(src)
            if limit and len(rows) >= limit:
                break
    return rows


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Load MultiEURLEX docs as Copilot Studio knowledge files.")
    ap.add_argument("--execute", action="store_true",
                    help="Create components + upload files. Without it, only validates and previews.")
    ap.add_argument("--limit", type=int, default=None, help="Process only the first N rows.")
    ap.add_argument("--overwrite", action="store_true",
                    help="Replace files that already exist on the agent (delete + recreate).")
    ap.add_argument("--clean", action="store_true",
                    help="Delete ALL existing file knowledge on the agent in one sweep first, "
                         "then load fresh (instead of per-row overwrite).")
    ap.add_argument("--no-publish", action="store_true",
                    help="Skip the PvaPublish step at the end.")
    ap.add_argument("--sleep", type=float, default=0.0,
                    help="Seconds to pause between uploads (throttle relief).")
    args = ap.parse_args()

    load_env()

    if not DATA_FILE.exists():
        print(f"ERROR: data file not found: {DATA_FILE}", flush=True)
        sys.exit(1)

    rows = load_rows(DATA_FILE, limit=args.limit)
    print(f"Parsed {len(rows)} documents from {DATA_FILE}")
    print(f"Target agent: MultiEURLEX Classic DV Knowledge ({BOT_ID})")

    # Duplicate celex check — filename must be unique.
    seen = {}
    for r in rows:
        c = r[KEY_COLUMN].strip()
        seen[c] = seen.get(c, 0) + 1
    dupes = {c: n for c, n in seen.items() if n > 1}
    if dupes:
        print(f"ERROR: duplicate celex_id values: {dupes}", flush=True)
        sys.exit(1)

    # Preview first document.
    if rows:
        celex0 = rows[0][KEY_COLUMN].strip()
        md = build_markdown(rows[0])
        print(f"\nSample component name : {celex0}")
        print(f"Sample uploaded file  : {celex0}.md ({len(md.encode('utf-8'))} bytes)")
        print(f"Sample description    : {build_description(rows[0])}")
        print("Sample file body (first lines):")
        for ln in md.splitlines()[:14]:
            print(f"    {ln[:90]}")
        print("    ...")

    if len(rows) > 250:
        print("\nNOTE: Copilot Studio agents have a max file-knowledge count; "
              f"{len(rows)} files may approach that limit. Verify in the portal after publish.")

    if not args.execute:
        print("\nDRY RUN — nothing written. Re-run with --execute to load.")
        return

    # ── Execute ─────────────────────────────────────────────────────────────
    token = get_token()
    existing = list_existing_files(token)
    print(f"\nAgent already has {len(existing)} file-attachment component(s).")

    if args.clean and existing:
        print(f"--clean: purging all {len(existing)} existing file(s) before load...", flush=True)
        purged = purge_all_files(token, existing)
        print(f"Purged {purged} file(s). Loading fresh.", flush=True)
        existing = {}  # bot is now empty — every row is a clean create

    created = skipped = replaced = failed = 0
    for i, row in enumerate(rows, 1):
        celex = row[KEY_COLUMN].strip()
        name = celex                       # component name = bare CELEX id
        upload_name = f"{celex}.md"        # uploaded file keeps .md so type is detected
        content = build_markdown(row).encode("utf-8")
        # Match either naming convention: bare CELEX (new) or "<celex>.md" (legacy
        # runs / the in-flight load) so reruns reconcile instead of duplicating.
        prior_key = name if name in existing else (upload_name if upload_name in existing else None)

        try:
            if prior_key is not None:
                if not args.overwrite:
                    skipped += 1
                    print(f"[{i}/{len(rows)}] skip (exists): {prior_key}", flush=True)
                    continue
                delete_component(token, existing[prior_key])
                replaced += 1

            cid = create_component(token, name, build_description(row), _schemaname(celex))
            try:
                upload_filedata(token, cid, upload_name, content)
            except Exception:
                # Roll back the just-created (empty) component so a rerun stays a
                # clean resume — a present name always means a complete file.
                try:
                    delete_component(token, cid)
                except Exception:
                    pass
                raise
            created += 1
            print(f"[{i}/{len(rows)}] uploaded: {name} ({upload_name}, {len(content)} bytes)", flush=True)
        except Exception as e:
            failed += 1
            print(f"[{i}/{len(rows)}] FAILED: {name}: {e}", flush=True)

        if args.sleep:
            time.sleep(args.sleep)

    print(f"\nUploaded {created} (replaced {replaced}), skipped {skipped}, failed {failed}.")

    if failed:
        print("Some uploads failed — fix and re-run (existing files are skipped). "
              "Not publishing.", flush=True)
        sys.exit(1)

    if args.no_publish:
        print("Skipping publish (--no-publish). Publish in Copilot Studio to make knowledge live.")
        return

    print("Publishing agent (PvaPublish)...", flush=True)
    publish_bot(token)
    print("Published. Knowledge files are live.")


if __name__ == "__main__":
    main()
