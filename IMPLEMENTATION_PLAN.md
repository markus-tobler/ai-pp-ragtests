# Implementation Plan

---

## Phase 1: Define The Test Corpus

Start from MultiEURLEX and build a local selection pipeline around the current get_test_data.py script.

The target corpus should contain:

- `300` documents total
- full document text
- documents between approximately `2` and `10` pages
- multiple languages if needed, but likely start with English
- a balanced spread across metadata dimensions
- a stable output file for import, probably `data/selected_multieurlex_300.csv` or `.jsonl`

Use `300 words = 1 page` as the first approximation, so the target document length range is:

```text
min_words = 600
max_words = 3000
```

The local selection process should:

1. Download/read MultiEURLEX locally.
2. Parse `celex_id`.
3. Compute word count and page estimate.
4. Filter to documents between `600` and `3000` words.
5. Add metadata dimensions.
6. Stratify/sample until 300 documents are selected.
7. Export both the final corpus and a selection report.

Suggested local outputs:

```text
data/raw/
data/processed/multieurlex_candidates.jsonl
data/processed/multieurlex_selected_300.jsonl
data/processed/multieurlex_selected_300.csv
reports/selection_summary.md
```

---

## Phase 2: Choose 5 Metadata Dimensions

Use controlled metadata fields with `5` to `20` possible values each. Some can be derived from MultiEURLEX/CELEX, while others may need deterministic extraction or enrichment.

Recommended first version:

| Dimension | Source | Target Values |
|---|---|---|
| `policy_domain` | EUROVOC level 1/domain or mapped topic group | 10-20 |
| `document_type` | CELEX document type | 5-10 |
| `year_band` | CELEX year | 5-8 |
| `legal_actor_type` | extracted/enriched from text | 5-12 |
| `applicable_role` | extracted/enriched from text | 5-15 |

Possible values:

`policy_domain`

```text
Agriculture
Transport
Environment
Finance
Trade
Justice
Employment
Health
Energy
Education
Industry
External relations
Regional policy
Consumer protection
Digital/data
```

`document_type`

```text
Regulation
Directive
Decision
Recommendation
Agreement
Communication
Proposal
Case law
Other
```

`year_band`

```text
1950-1979
1980-1989
1990-1999
2000-2009
2010-2014
2015-2019
2020-2026
```

`legal_actor_type`

```text
EU institution
Member state authority
National court
Public agency
Company
Financial institution
Employer
Worker
Consumer/citizen
Non-EU country
International organization
```

`applicable_role`

```text
Regulated entity
Competent authority
Applicant
Beneficiary
Supplier
Importer/exporter
Operator
Consumer
Data subject
Employer
Employee
Public body
Financial intermediary
```

Location can be added either as a sixth dimension or substituted for `year_band`. If included, keep it controlled:

```text
EU-wide
Germany
France
Italy
Spain
Netherlands
Belgium
Poland
Austria
Sweden
Other member state
Non-EU
```

Important design choice: distinguish between metadata that is genuinely present in the source and metadata inferred for testing. For example:

```text
metadata_source = "celex"
metadata_source = "eurovoc"
metadata_source = "rule_based"
metadata_source = "llm_enriched"
```

This helps later when evaluating whether search quality is coming from real document structure or synthetic enrichment.

---

## Phase 3: Selection Strategy For 300 Texts

Create a repeatable selection algorithm rather than hand-picking records.

Recommended approach:

1. Filter by length: `600 <= word_count <= 3000`.
2. Remove records with missing text or malformed `celex_id`.
3. Compute all five metadata dimensions.
4. Assign each document to a length level:

```text
short: 2-4 pages
medium: 4-7 pages
long: 7-10 pages
```

5. Select approximately:

```text
100 short
100 medium
100 long
```

6. Within each length level, balance across `policy_domain`, `document_type`, and `year_band`.
7. Avoid over-representation of any single value where possible.
8. Save a selection summary showing final counts per dimension.

The selection does not need to be perfectly balanced, but it should avoid obvious skew, such as 250 regulations from one decade.

Acceptance criteria for the selected data:

- exactly `300` rows
- every row has full text
- every row has the five metadata dimensions
- every metadata dimension has between `5` and `20` distinct values
- all documents are estimated between `2` and `10` pages
- no duplicate `celex_id`
- selection can be recreated with a fixed random seed

---

## Phase 4: Prepare The Dataverse Table

Create one main Dataverse table for all texts.

Suggested table name:

```text
rag_multieurlex_document
```

Suggested columns:

| Column | Type | Max Length | Notes |
|---|---|---|---|
| `celex_id` | Single Line of Text | 50 | Alternate key / unique identifier; typical CELEX IDs are 10-20 chars |
| `title` | Single Line of Text | 500 | EU legal titles can exceed 200 chars |
| `language` | Single Line of Text | 10 | ISO 639-1 code, e.g. `en` |
| `document_text` | Multiple Lines of Text | 100,000 | ~3,000 words × ~5 chars/word + markup overhead |
| `word_count` | Whole number | — | For filtering/evaluation |
| `page_estimate` | Decimal | — | For filtering/evaluation |
| `length_level` | Single Line of Text | 20 | Values: short, medium, long |
| `policy_domain` | Single Line of Text | 100 | Longest controlled value ~25 chars (e.g. `Consumer protection`) |
| `document_type` | Single Line of Text | 100 | Longest controlled value ~15 chars (e.g. `Recommendation`) |
| `year` | Whole number | — | Parsed from CELEX |
| `year_band` | Single Line of Text | 20 | Format `YYYY-YYYY`, 9 chars |
| `legal_actor_type` | Single Line of Text | 100 | Longest controlled value ~28 chars (e.g. `International organization`) |
| `applicable_role` | Single Line of Text | 100 | Longest controlled value ~24 chars (e.g. `Financial intermediary`) |
| `location_scope` | Single Line of Text | 100 | Longest controlled value ~20 chars (e.g. `Other member state`) |
| `metadata_json` | Multiple Lines of Text | 10,000 | Raw/enriched metadata JSON for audit |
| `source_dataset` | Single Line of Text | 100 | e.g. `MultiEURLEX` |
| `source_split` | Single Line of Text | 50 | e.g. `test`, `train`, `validation` |
| `selection_batch` | Single Line of Text | 50 | e.g. `ragtest-001` |

> **Note on column type choice**: Metadata dimensions use `Single Line of Text` rather than `Choice`/Option Set. Both types are indexed by Dataverse Search (full-text index), but `Choice` stores integer option codes — OData filter expressions via MCP would require numeric values (`policy_domain eq 100000003`) instead of readable strings (`policy_domain eq 'Environment'`). Plain text columns keep MCP queries simple and vocabulary-agnostic. Controlled vocabulary enforcement is handled in the data pipeline (Phase 3).

For search and filtering, Dataverse views should be prepared for:

- all documents
- by policy domain
- by document type
- by length level
- by year band
- by applicable role
- by legal actor type

---

## Phase 5: Load Data Into Dataverse

Use `microsoft/Dataverse-skills` for this part.

Planned flow:

1. Install/connect Dataverse Skills.
2. Run the equivalent of “Connect to Dataverse”.
3. Confirm the target environment.
4. Create a solution for the test assets.
5. Create the `rag_multieurlex_document` table.
6. Create required choice columns.
7. Configure `celex_id` as an alternate key.
8. Import the selected CSV/JSON data.
9. Validate record counts and sample records.

Validation checklist:

```text
Dataverse table exists
300 records loaded
celex_id is unique
document_text is populated
metadata columns are populated
choice values match the controlled vocabularies
views return expected records
```

Use bulk import/upsert rather than manual record creation. The Dataverse Skills `dv-data` and `dv-metadata` capabilities are the best fit here.

---

## Phase 6: Create The Copilot Studio Agent

Create a Copilot Studio agent whose purpose is to search and answer questions over the 300 legal/policy documents.

Agent purpose:

```text
Search a curated MultiEURLEX legal document corpus stored in Dataverse and answer questions using the document text plus structured metadata.
```

The agent should support at least these test query types:

```text
Find documents about environmental regulation for operators.
Find directives from 2010-2019 related to employment.
Show short documents involving member state authorities.
Search for texts applicable to financial institutions.
Find documents mentioning Germany in transport policy.
Summarize the most relevant documents for consumer protection.
```

The agent should be connected to Dataverse through the Dataverse MCP server, using the authenticated environment and the prepared table.

Initial agent behavior should be constrained:

- search only the selected Dataverse table
- return source `celex_id`
- use metadata filters when the user mentions them
- summarize from document text only
- avoid presenting inferred metadata as legal fact
- include “no matching document found” behavior

---

## Phase 7: Evaluation Plan

Prepare a small test suite before optimizing the agent.

Create around `30` evaluation prompts:

- `10` metadata-only search questions
- `10` semantic/full-text questions
- `5` mixed metadata + semantic questions
- `5` negative/control questions where no result should match

For each prompt, record:

```text
expected metadata filters
expected matching celex_id values, if known
expected answer shape
actual answer
source records returned
pass/fail
notes
```

Measure:

- whether the right records are retrieved
- whether metadata filters are respected
- whether answers cite or identify source documents
- whether long text fields are searchable enough through the chosen Dataverse/MCP approach
- whether the agent confuses inferred metadata with source facts

---

## Phase 8: Development Milestones

A practical sequence for future development:

1. Refactor get_test_data.py into a reusable local preparation script.
2. Add deterministic filtering by document length.
3. Add CELEX parsing and native metadata extraction.
4. Add controlled metadata enrichment for legal actor, role, and location.
5. Implement stratified sampling for exactly 300 documents.
6. Export CSV/JSONL plus a selection summary report.
7. Install and connect `Dataverse-skills`.
8. Create the Dataverse solution and table.
9. Load the 300 records.
10. Validate Dataverse data quality.
11. Create the Copilot Studio agent with Dataverse MCP access.
12. Run the evaluation prompts.
13. Iterate on table schema, metadata choices, and agent instructions.

## Key Decision
For this test, treat `microsoft/Dataverse-skills` as the main implementation path. Bring in `microsoft/power-platform-skills` later only if you decide to build a Power Platform app or richer UI around the corpus.