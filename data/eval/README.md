# MultiEURLEX Search Agent — Evaluation Test Set (20 questions)

Question/answer evaluation set derived from the actual corpus
`data/processed/multieurlex_selected_300.csv`. Every expected answer is grounded
in a real document in that corpus (traceable by `celex_id`).

## Files

| File | Purpose |
|------|---------|
| `multieurlex_eval_set_source.csv` | **Source of truth** for humans. Full record: question, precise expected answer, behavioral rubric, grounding doc (`celex_id` + title), the metadata dimensions used, the difficulty tier, and (for tricky cases) the distractor doc ids that look like answers but are ruled out. |
| `multieurlex_eval_set_copilot_import_conversation.csv` | **Import file** — *Import conversations* template (`EvalConversationTemplate.csv`). `#` comment block, then `conversationNumber`, `question`, `response`. Each of the 20 questions is its own conversation (one Q&A pair) so the tricky cases never share context. `response` is reference-only (not compared). |
| `multieurlex_eval_set_copilot_import_classic.csv` | **Import file** — *classic* single-response template (`EvaluationTemplate_classic.csv`). `#` comment block, then `question`, `expectedResponse`. Here `expectedResponse` **is** used by the match / similarity / compare-meaning test methods. |
| `EvalConversationTemplate.csv` / `EvaluationTemplate_classic.csv` | The two official Copilot Studio templates the import files are modelled on (reference). |
| `../../scripts/build_eval_set.py` | Generator. All CSVs are produced from one table in this script, so they never drift. Re-run after editing. |

Pick the import file that matches the evaluation type you start in Copilot
Studio: the **conversation** file for multi-turn / *Import conversations*, or the
**classic** file for single-response evaluation where the expected answer is
graded.

Regenerate:

```bash
python3 scripts/build_eval_set.py
```

## Difficulty tiers (metadata richness)

The set deliberately spans how much metadata context the question carries, per
the request:

| Tier | Count | What it tests |
|------|-------|---------------|
| **A** | 5 | Few metadata cues — broad topical question, one obvious matching document. |
| **B** | 5 | Medium — ~2 metadata constraints (e.g. year + domain). |
| **C** | 5 | Precise — 3+ constraints (year + type + domain + topic) pinpoint a single doc, answer includes an exact fact/figure. |
| **D** | 5 | **Tricky** — several documents are plausible candidate answers; metadata stated in the question (country, date, subject, document type) rules all but one out. |

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
   - *Import conversations* → `multieurlex_eval_set_copilot_import_conversation.csv`
   - single-response / classic → `multieurlex_eval_set_copilot_import_classic.csv`
4. Review the imported cases — 20 in either file. All import with the default
   **General quality** grader.
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
  conversation so the tricky cases cannot leak context to one another.
- **Classic** template: max **100** questions, max **500** chars per question.
  `expectedResponse` is used by match / similarity / compare-meaning methods.
- The generator enforces all of the above. Set test methods (and their
  thresholds / keywords) in the UI after import.

## Grounding

Each answer traces to one corpus document via `source_celex_id` in the source
CSV. The corpus is English-only (`language=en`), 300 documents, document types
Regulation / Decision / Directive, years 2012–2015.
