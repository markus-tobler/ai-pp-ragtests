"""Phase 5: Load selected MultiEURLEX corpus into is_rag_multieurlex_document.

Inspired by the dv-data skill's bulk-import pattern. Reads the 300 selected
records from data/processed/multieurlex_selected_300.jsonl and upserts them into
the Dataverse table created in Phase 4.

Why upsert (not create):
  Idempotent — re-running does NOT create duplicates. The table has an alternate
  key `is_rag_multieurlex_celex_key` on `is_celex_id`, so each record is keyed by
  its CELEX ID. Per the dv-data skill, the alternate-key column must NOT appear in
  the record body, so `celex_id` goes in `alternate_key` and everything else in
  `record`.

Why JSONL (not CSV):
  document_text contains embedded newlines, which makes the CSV span thousands of
  physical lines. The JSONL file holds exactly one record per line — safe to parse.

Usage:
    python scripts/04_dv_load_corpus.py            # DRY RUN — validates + previews, no write
    python scripts/04_dv_load_corpus.py --execute  # perform the upsert
    python scripts/04_dv_load_corpus.py --execute --limit 5   # load only first 5 (smoke test)
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from auth import get_client, load_env

TABLE = "is_rag_multieurlex_document"
ALTERNATE_KEY_COLUMN = "is_celex_id"
DATA_FILE = Path("data/processed/multieurlex_selected_300.jsonl")

# Source JSONL field -> Dataverse logical column name.
# celex_id is intentionally absent: it is the alternate key, not a body field.
FIELD_MAP = {
    "title": "is_title",
    "language": "is_language",
    "document_text": "is_document_text",
    "word_count": "is_word_count",
    "page_estimate": "is_page_estimate",
    "length_level": "is_length_level",
    "policy_domain": "is_policy_domain",
    "document_type": "is_document_type",
    "year": "is_year",
    "year_band": "is_year_band",
    "legal_actor_type": "is_legal_actor_type",
    "applicable_role": "is_applicable_role",
    "metadata_json": "is_metadata_json",
    "source_dataset": "is_source_dataset",
    "source_split": "is_source_split",
    "selection_batch": "is_selection_batch",
}

# Columns that exist on the table but are not populated by this dataset.
# Left unset deliberately — documented here so the gap is intentional, not a bug.
UNMAPPED_TABLE_COLUMNS = ["is_location_scope", "is_metadata_source"]


def load_records(path, limit=None):
    """Parse JSONL into (alternate_key, record_body) pairs ready for upsert."""
    rows = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                src = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  ! skipping malformed line {line_no}: {e}", flush=True)
                continue

            celex = (src.get("celex_id") or "").strip()
            if not celex:
                print(f"  ! skipping line {line_no}: missing celex_id", flush=True)
                continue

            body = {}
            for src_key, col in FIELD_MAP.items():
                val = src.get(src_key)
                if val is None or val == "":
                    continue
                body[col] = val

            rows.append((celex, body))
            if limit and len(rows) >= limit:
                break
    return rows


def main():
    parser = argparse.ArgumentParser(description="Load selected MultiEURLEX corpus into Dataverse.")
    parser.add_argument("--execute", action="store_true",
                        help="Perform the upsert. Without this flag the script only validates and previews.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Load only the first N records (smoke test).")
    parser.add_argument("--chunk-size", type=int, default=50,
                        help="Records per UpsertMultiple batch. Lower for wide rows with large text columns.")
    args = parser.parse_args()

    load_env()

    if not DATA_FILE.exists():
        print(f"ERROR: data file not found: {DATA_FILE}", flush=True)
        sys.exit(1)

    rows = load_records(DATA_FILE, limit=args.limit)
    print(f"Parsed {len(rows)} records from {DATA_FILE}")
    print(f"Target table: {TABLE}  |  alternate key column: {ALTERNATE_KEY_COLUMN}")
    print(f"Unmapped (left blank): {', '.join(UNMAPPED_TABLE_COLUMNS)}")

    # Duplicate celex check — alternate key must be unique.
    seen = {}
    for celex, _ in rows:
        seen[celex] = seen.get(celex, 0) + 1
    dupes = {c: n for c, n in seen.items() if n > 1}
    if dupes:
        print(f"ERROR: duplicate celex_id values found: {dupes}", flush=True)
        sys.exit(1)

    # Preview first record's column coverage.
    if rows:
        sample_celex, sample_body = rows[0]
        print(f"\nSample record [{sample_celex}] columns set: {len(sample_body)}")
        for col in sorted(sample_body):
            val = sample_body[col]
            preview = (str(val)[:60] + "...") if len(str(val)) > 60 else val
            print(f"    {col:<22} = {preview!r}")

    if not args.execute:
        print("\nDRY RUN — no data written. Re-run with --execute to load.")
        return

    # ── Upsert ────────────────────────────────────────────────────────────────
    from PowerPlatform.Dataverse.models.upsert import UpsertItem

    client = get_client("dv-data")

    items = [
        UpsertItem(alternate_key={ALTERNATE_KEY_COLUMN: celex}, record=body)
        for celex, body in rows
    ]

    total = len(items)
    done = 0
    for i in range(0, total, args.chunk_size):
        chunk = items[i:i + args.chunk_size]
        client.records.upsert(TABLE, chunk)
        done += len(chunk)
        print(f"Upserted {done}/{total}", flush=True)

    print(f"\nDone. {done} records upserted into {TABLE}.")


if __name__ == "__main__":
    main()
