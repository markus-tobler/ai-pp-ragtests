"""Phase 4: Create is_rag_multieurlex_document table in Dataverse."""
import os, sys, time, json, urllib.request, urllib.error
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from auth import get_client, get_token, get_plugin_headers, load_env

load_env()
DATAVERSE_URL = os.environ["DATAVERSE_URL"].rstrip("/")
SOLUTION = os.environ["SOLUTION_NAME"]

client = get_client("dv-metadata")

TABLE = "is_rag_multieurlex_document"
DISPLAY = "RAG MultiEURLEX Document"


def label(text):
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [
            {"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel", "Label": text, "LanguageCode": 1033}
        ],
    }


def webapi(method, path, body=None):
    headers = get_plugin_headers("dv-metadata", get_token())
    headers["MSCRM.SolutionUniqueName"] = SOLUTION
    headers["OData-MaxVersion"] = "4.0"
    headers["OData-Version"] = "4.0"
    headers["Accept"] = "application/json"
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    url = f"{DATAVERSE_URL}/api/data/v9.2/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"  HTTP {e.code} {method} {path}: {err[:400]}")
        raise


# ── Step 1: Create table ─────────────────────────────────────────────────────

existing = client.tables.get(TABLE)
if existing:
    print(f"Table already exists: {TABLE} — skipping creation")
else:
    print(f"Creating table {TABLE}...")
    entity = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": "is_rag_multieurlex_document",
        "DisplayName": label(DISPLAY),
        "DisplayCollectionName": label("RAG MultiEURLEX Documents"),
        "Description": label("MultiEURLEX legal document corpus for RAG testing"),
        "OwnershipType": "UserOwned",
        "HasActivities": False, "HasNotes": False, "IsActivity": False,
        "PrimaryNameAttribute": "is_celex_id",
        "Attributes": [{
            "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
            "SchemaName": "is_celex_id",
            "DisplayName": label("CELEX ID"),
            "Description": label("Unique CELEX identifier, e.g. 32019L0001"),
            "RequiredLevel": {"Value": "ApplicationRequired"},
            "MaxLength": 50,
            "IsPrimaryName": True,
        }],
    }
    webapi("POST", "EntityDefinitions", entity)
    print("Table created. Waiting 20s for metadata propagation...")
    time.sleep(20)

# Force cache refresh
webapi("GET", f"EntityDefinitions(LogicalName='{TABLE}')?$select=LogicalName")
print("Cache refreshed. Adding columns...")


# ── Step 2: Add columns ───────────────────────────────────────────────────────

def add_string(schema, display, max_len, required=False, description=""):
    col = {
        "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
        "SchemaName": schema, "DisplayName": label(display),
        "Description": label(description),
        "RequiredLevel": {"Value": "ApplicationRequired" if required else "None"},
        "MaxLength": max_len,
    }
    try:
        webapi("POST", f"EntityDefinitions(LogicalName='{TABLE}')/Attributes", col)
        print(f"  + {schema} (string/{max_len})")
    except Exception:
        print(f"  ~ {schema} (may already exist)")


def add_memo(schema, display, max_len, description=""):
    col = {
        "@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
        "SchemaName": schema, "DisplayName": label(display),
        "Description": label(description),
        "RequiredLevel": {"Value": "None"}, "MaxLength": max_len,
    }
    try:
        webapi("POST", f"EntityDefinitions(LogicalName='{TABLE}')/Attributes", col)
        print(f"  + {schema} (memo/{max_len})")
    except Exception:
        print(f"  ~ {schema} (may already exist)")


def add_int(schema, display, description=""):
    col = {
        "@odata.type": "Microsoft.Dynamics.CRM.IntegerAttributeMetadata",
        "SchemaName": schema, "DisplayName": label(display),
        "Description": label(description),
        "RequiredLevel": {"Value": "None"}, "MinValue": 0, "MaxValue": 2147483647,
    }
    try:
        webapi("POST", f"EntityDefinitions(LogicalName='{TABLE}')/Attributes", col)
        print(f"  + {schema} (int)")
    except Exception:
        print(f"  ~ {schema} (may already exist)")


def add_decimal(schema, display, description=""):
    col = {
        "@odata.type": "Microsoft.Dynamics.CRM.DecimalAttributeMetadata",
        "SchemaName": schema, "DisplayName": label(display),
        "Description": label(description),
        "RequiredLevel": {"Value": "None"},
        "MinValue": 0, "MaxValue": 10000, "Precision": 2,
    }
    try:
        webapi("POST", f"EntityDefinitions(LogicalName='{TABLE}')/Attributes", col)
        print(f"  + {schema} (decimal)")
    except Exception:
        print(f"  ~ {schema} (may already exist)")


add_string("is_title",           "Title",            500, required=True,  description="EU legal document title")
add_string("is_language",        "Language",         10,                  description="ISO 639-1 code e.g. en")
add_string("is_length_level",    "Length Level",     20,                  description="short, medium, or long")
add_string("is_policy_domain",   "Policy Domain",    100,                 description="Controlled vocabulary")
add_string("is_document_type",   "Document Type",    100,                 description="e.g. Regulation, Directive")
add_string("is_year_band",       "Year Band",        20,                  description="e.g. 2010-2014")
add_string("is_legal_actor_type","Legal Actor Type", 100,                 description="e.g. EU institution")
add_string("is_applicable_role", "Applicable Role",  100,                 description="e.g. Regulated entity")
add_string("is_location_scope",  "Location Scope",   100,                 description="e.g. EU-wide, Germany")
add_string("is_source_dataset",  "Source Dataset",   100,                 description="e.g. MultiEURLEX")
add_string("is_source_split",    "Source Split",     50,                  description="e.g. test, train")
add_string("is_selection_batch", "Selection Batch",  50,                  description="e.g. ragtest-001")
add_string("is_metadata_source", "Metadata Source",  50,                  description="celex, eurovoc, rule_based, llm_enriched")

add_memo("is_document_text",     "Document Text",    100000,              description="Full document text")
add_memo("is_metadata_json",     "Metadata JSON",    10000,               description="Raw/enriched metadata for audit")

add_int("is_word_count",         "Word Count",                            description="Computed word count")
add_int("is_year",               "Year",                                  description="Publication year from CELEX")
add_decimal("is_page_estimate",  "Page Estimate",                         description="Estimated pages (300 words=1 page)")

print("\nWaiting 15s before alternate key...")
time.sleep(15)


# ── Step 3: Alternate key on celex_id ────────────────────────────────────────

print("Creating alternate key on is_celex_id...")
try:
    existing_keys = client.tables.get_alternate_keys(TABLE)
    key_names = [k.get("SchemaName", "") for k in (existing_keys or [])]
    if any("celex" in k.lower() for k in key_names):
        print("  Alternate key already exists.")
    else:
        client.tables.create_alternate_key(
            TABLE, "is_rag_multieurlex_celex_key", ["is_celex_id"], display_name="CELEX ID Key"
        )
        print("  Alternate key created (index building async).")
except Exception as e:
    print(f"  ! Alternate key: {e}")


# ── Summary ───────────────────────────────────────────────────────────────────

print("\n=== Column Summary ===")
cols = [
    ("is_celex_id",          "String",  50,     "PrimaryName + alternate key"),
    ("is_title",             "String",  500,    "required"),
    ("is_language",          "String",  10,     ""),
    ("is_document_text",     "Memo",    100000, ""),
    ("is_word_count",        "Int",     "-",    ""),
    ("is_page_estimate",     "Decimal", "-",    ""),
    ("is_length_level",      "String",  20,     ""),
    ("is_policy_domain",     "String",  100,    ""),
    ("is_document_type",     "String",  100,    ""),
    ("is_year",              "Int",     "-",    ""),
    ("is_year_band",         "String",  20,     ""),
    ("is_legal_actor_type",  "String",  100,    ""),
    ("is_applicable_role",   "String",  100,    ""),
    ("is_location_scope",    "String",  100,    ""),
    ("is_metadata_json",     "Memo",    10000,  ""),
    ("is_source_dataset",    "String",  100,    ""),
    ("is_source_split",      "String",  50,     ""),
    ("is_selection_batch",   "String",  50,     ""),
    ("is_metadata_source",   "String",  50,     ""),
]
print(f"{'Logical Name':<30} {'Type':<10} {'MaxLen':>7}  Notes")
print("-" * 65)
for name, typ, ml, notes in cols:
    print(f"{name:<30} {typ:<10} {str(ml):>7}  {notes}")
print(f"\nTable: {TABLE}  |  Solution: {SOLUTION}")
