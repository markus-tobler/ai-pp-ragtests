# Evaluate-tab CSV exports (drop folder)

Put the CSV files exported from the Copilot Studio **Evaluate** tab here, then run:

```bash
python3 scripts/collect_eval_results.py
```

## Layout: one subfolder per run

For multiple runs (e.g. different models/configs), make **one subfolder per
run** — the folder name is the run label. Export filenames stay as-is (they only
differ by timestamp); the folder disambiguates them:

```
data/eval/exports/
  gpt-4o/                                          <- run label
    Evaluate MultiEURLEX Classic MCP 260628_1822.csv
    Evaluate MultiEURLEX Classic Knowledge 260628_1830.csv
    ...
  gpt-4o-mini/                                     <- another run
    Evaluate MultiEURLEX Classic MCP 260629_0900.csv
    ...
```

Each run -> `data/eval/results/<run-label>/` (per-agent JSON + summary.csv/json).
With 2+ runs you also get `data/eval/results/comparison.csv` (+ `.json`): an
**agent x run pass-rate matrix** for comparing models side by side.

Loose CSVs placed directly in this folder (no subfolder) are treated as one run
labeled `default` (override with `--run-name`).

This is the interim path while the maker-evaluation **REST API is unavailable**
in this environment (the `makerevaluation/*` routes 404 `RouteNotFound` — a
Microsoft Preview rollout gap; `scripts/run_agent_evals.py` is correct and will
work once they deploy).

## How to export

1. Copilot Studio → open the agent → **Evaluate** tab.
2. Run the `Evaluate <agent>` test set (or open a completed run).
3. **Export** the results to CSV (downloads as `Evaluate <agent name> <date>.csv`).
4. Move the file into this folder.

Files are matched to agents by the agent name in the file name, so keep the
default `Evaluate <agent name> ...` naming. Output lands in
`data/eval/results/run_<timestamp>/`.
