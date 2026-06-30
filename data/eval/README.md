# MultiEURLEX Search Agent — Evaluation Test Set (50 questions)

Question/answer evaluation set derived from the actual corpus
`data/processed/multieurlex_selected_300.csv`. Every grounded answer traces to a
real document in that corpus (by `celex_id`).

Each question carries a human-readable **metadata filter block** listing only the
metadata the question actually constrains (e.g. `Year: 2014`, `Document type:
Regulation`, `Policy domain: Finance`), so the agent can turn it straight into an
AND'd WHERE clause. Each grounded expected answer **leads with the CELEX id**
(`CELEX <id> - ...`), matching the agent's required output. Tier A and tier S
questions carry no filter block; tier D filter blocks deliberately match more
than one document, so the disambiguator stays in the prose.

## Folder layout

Generated artifacts are kept in tidy sub-folders, not loose in `data/eval/`:

| Folder | Contents |
|--------|----------|
| `test_sets/` | The generated eval-set CSVs (overall + per-tier). |
| `documents/` | One lightly-formatted PDF per corpus document (`<celex_id>.pdf`). |
| `templates/` | The two reference Copilot Studio import templates. |
| `exports/` · `results/` · `analysis/` | Raw run exports, collected results, and charts. |

All of `test_sets/` and `documents/` are produced by `scripts/build_eval_set.py`.

## Files

### Overall set (all 50 questions) — `test_sets/`

| File | Purpose |
|------|---------|
| `multieurlex_eval_set_source.csv` | **Source of truth** for humans. Full record: question (with filter block), the `filters` applied, precise expected answer (CELEX-prefixed), behavioral rubric, grounding doc (`celex_id` + title), the metadata dimensions used, the difficulty tier, and (for tricky cases) the distractor doc ids that look like answers but are ruled out. |
| `multieurlex_eval_set_copilot_import_conversation.csv` | **Import file** — *Import conversations* template (`EvalConversationTemplate.csv`). `#` comment block, then `conversationNumber`, `question`, `response`. Each question is its own conversation (one Q&A pair) so the tricky cases never share context. `response` is reference-only (not compared). |
| `multieurlex_eval_set_copilot_import_classic.csv` | **Import file** — *classic* single-response template (`EvaluationTemplate_classic.csv`). `#` comment block, then `question`, `expectedResponse`. Here `expectedResponse` **is** used by the match / similarity / compare-meaning test methods. |

### Per-tier sets (run one question type in isolation)

Each tier is also emitted as its own standalone, independently-runnable pair, so
a single question type can be imported and evaluated on its own:

| File pattern | Tiers |
|---|---|
| `multieurlex_eval_set_tier<X>_copilot_import_classic.csv` | A, B, C, D, E, S |
| `multieurlex_eval_set_tier<X>_copilot_import_conversation.csv` | A, B, C, D, E, S |

Same two formats and the same `#` comment blocks / limits as the overall files —
just filtered to one tier. Useful e.g. to run **only the semantic tier (S)**
against the semantic agent, or **only the unanswerable tier (E)** to check
abstention behaviour.

### Document PDFs — `documents/`

One PDF per corpus document, named `<celex_id>.pdf` (300 files). Each page shows a
clear **title**, a formatted **metadata block** (CELEX id, document type, policy
domain, year, legal actor type, applicable role, language), then the **full
document text**. The metadata is printed on the page only — it is deliberately
**not** written into the PDF's file/document properties (those are left blank).
Useful for ingesting the corpus as real documents (e.g. into a knowledge source).

### Reference / generator

| File | Purpose |
|------|---------|
| `templates/EvalConversationTemplate.csv` / `templates/EvaluationTemplate_classic.csv` | The two official Copilot Studio templates the import files are modelled on (reference). |
| `../../scripts/build_eval_set.py` | Generator. All CSVs (overall + per-tier) **and** the per-document PDFs are produced from one table / the corpus in this script, so they never drift. Re-run after editing. |

Pick the import file that matches the evaluation type you start in Copilot
Studio: the **conversation** file for multi-turn / *Import conversations*, or the
**classic** file for single-response evaluation where the expected answer is
graded.

Regenerate:

```bash
python3 scripts/build_eval_set.py
```

## Difficulty / capability tiers

The set deliberately spans how much metadata context the question carries, plus a
dedicated semantic-search tier:

| Tier | Count | What it tests |
|------|-------|---------------|
| **A** | 9 | Few metadata cues — broad topical question, one obvious matching document. |
| **B** | 11 | Medium — ~2 metadata constraints (e.g. year + domain). |
| **C** | 8 | Precise — 3+ constraints (year + type + domain + topic) pinpoint a single doc, answer includes an exact fact/figure. |
| **D** | 7 | **Tricky** — several documents are plausible candidate answers; metadata stated in the question (country, date, subject, document type) rules all but one out. |
| **E** | 5 | **Unanswerable** — no corpus document answers; the agent must say the documents do not precisely answer and invent no CELEX id. |
| **S** | 10 | **Semantic** — the question is worded entirely in synonyms / paraphrases that share no literal term with the grounding document, so a keyword/literal match fails and only a semantic (embedding) match retrieves the right act. |

### The semantic (Tier S) cases

Tier S exists to isolate whether the retrieval path actually does **semantic**
matching rather than literal keyword overlap. Each question describes a real
corpus document using only everyday synonyms for its subject — never the
document's own terminology — and carries **no** metadata filter block, so meaning
alone has to carry the retrieval. Examples:

- *"flimsy throwaway shopping sacks"* → lightweight plastic carrier bags
  (`2015/720`).
- *"the sweet substance produced by bees … the floral material the insects
  gather"* → honey / pollen (`2014/63/EU`).
- *"portable power cells … small round cells containing mercury"* → batteries /
  button cells (`2013/56/EU`).
- *"carbon-allowance trading scheme for airline flights"* → Emissions Trading
  System for aviation (`421/2014`).

Run the tier-S file against each retrieval variant (mcp / semantic / hybrid /
knowledge) to compare how well each recovers the right document with no lexical
overlap.

### The tricky (Tier D) cases

Copilot Studio Evaluate passes **only the question string** to the agent — there
is no separate metadata-filter input. So for the tricky cases the disambiguating
metadata is woven into the question wording itself. Each has documented
distractors in the source CSV:

- **Q16 / Q17** — three near-identical EU–third-country Association Council
  decisions (Moldova `2015/55`, Ukraine `2015/60`, Georgia `2015/54`). Q16 uses
  *country*; Q17 uses *date (17 Nov 2014) + country*, which also excludes Ukraine
  (dated 15 Dec 2014).
- **Q18 / Q19** — two 2015 ECB Finance decisions (`ECB/2015/1` public access vs
  `ECB/2015/5` TLTROs). Disambiguated by *subject*.
- **Q20** — three "substances" documents (pesticide MRLs `2015/401`, biocidal
  `2013/5/EU`, RoHS `2015/863`). Disambiguated by *document type + subject (RoHS /
  EEE)*.

## How to use in Copilot Studio (Evaluate tab)

1. Open the agent in Copilot Studio.
2. Go to the **Evaluate** tab.
3. **New evaluation** → choose the type, then drag/browse the matching file:
   - *Import conversations* → a `..._copilot_import_conversation.csv`
   - single-response / classic → a `..._copilot_import_classic.csv`
   - to test one question type only, pick the matching `..._tier<X>_...` file.
4. Review the imported cases. All import with the default **General quality**
   grader.
5. For the precise/tricky cases, switch the test method in the UI to **Compare
   meaning** or **Keyword match** (e.g. the regulation number, "Article 486",
   "10 basis points", "90 ... 2019"). In the **classic** file the
   `expectedResponse` column already feeds these graders; in the
   **conversation** file the `response` column is reference-only (not compared),
   so enter the expected text in the UI.
6. **Evaluate** to run, or **Save** to run later.

### Notes / limits

- **Conversation** template: max **8** Q&A pairs per conversation, max **50**
  conversations, max **500** chars per question. Each question is a standalone
  conversation so the tricky cases cannot leak context to one another. (The
  overall set has exactly 50 conversations — at the cap.)
- **Classic** template: max **100** questions, max **500** chars per question.
  `expectedResponse` is used by match / similarity / compare-meaning methods.
- The generator enforces all of the above. Set test methods (and their
  thresholds / keywords) in the UI after import.

## Grounding

Each grounded answer traces to one corpus document via `source_celex_id` in the
source CSV (tier-E rows carry none by design). The corpus is English-only
(`language=en`), 300 documents, document types Regulation / Decision / Directive,
years 2012–2015.
