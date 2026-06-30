#!/usr/bin/env python3
"""Collect Copilot Studio Evaluate-tab CSV exports into a combined result set.

Interim path while the maker-evaluation REST API is unavailable in this
environment (see docs/EVAL_APP_REGISTRATION.md note / project memory). Run each
agent's test set in the Copilot Studio **Evaluate** tab, export the result CSV,
drop the files in one folder, then run this script to produce the same kind of
roll-up `07_eval_run.py` would have written.

Input: a directory of CSV files exported from the Evaluate tab. Each file is
typically named like `Evaluate <agent name> <date>.csv`. Export CSV columns (the
`_N` block repeats per eval method):

    question, expectedResponse, actualResponse,
    testMethodType_1, result_1, passingScore_1, explanation_1,
    testMethodType_2, result_2, ...

Output: data/eval/results/run_<UTC-ts>/
    <agent-slug>.json   - merged rows + summary for that agent
    summary.csv         - one row per agent: totals, pass rate, per-method tally
    summary.json        - machine-readable, includes per-method tallies

Agent attribution: each CSV is matched to an agent in agent-instructions/README.md
by finding the agent whose name appears in the file name (longest match wins).
Unmatched files still get collected, keyed by their file stem.

Multiple files per agent: if several CSVs in one run (folder) map to the same
agent, their rows are merged into that agent's single record. Rows are
de-duplicated by question text, with the later file winning (so dropping a fresh
re-export of one agent overrides its older rows). Files are ordered by name, and
exports are timestamped, so the newest export wins.

Usage:
    python3 scripts/08_eval_collect.py                       # reads data/eval/exports/
    python3 scripts/08_eval_collect.py --input-dir <dir>
    python3 scripts/08_eval_collect.py file1.csv file2.csv   # explicit files
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# reuse agent parsing + helpers from the sibling script. Its module name starts
# with a digit (07_eval_run), which a normal `import` can't load, so pull it in
# by file path via importlib.
import importlib.util  # noqa: E402

_run_path = Path(__file__).resolve().parent / "07_eval_run.py"
_spec = importlib.util.spec_from_file_location("eval_run", _run_path)
_eval_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_eval_run)
REPO_ROOT, parse_agents, slugify = (
    _eval_run.REPO_ROOT,
    _eval_run.parse_agents,
    _eval_run.slugify,
)

DEFAULT_INPUT_DIR = REPO_ROOT / "data" / "eval" / "exports"
RESULTS_ROOT = REPO_ROOT / "data" / "eval" / "results"

PASS = "pass"
FAIL = "fail"


def rel(p: Path) -> str:
    """Repo-relative path for display, or absolute if outside the repo."""
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def method_indices(fieldnames: list[str]) -> list[str]:
    """Return the sorted set of N suffixes present as testMethodType_N."""
    idx = []
    for f in fieldnames or []:
        m = re.fullmatch(r"testMethodType_(\d+)", f.strip())
        if m:
            idx.append(m.group(1))
    return sorted(idx, key=int)


def parse_rows(path: Path) -> list[dict]:
    """Parse one export CSV into normalized per-case rows."""
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        indices = method_indices(reader.fieldnames or [])
        rows = []
        for raw in reader:
            # skip the leading '#' comment/blank lines some exports carry
            q = (raw.get("question") or "").strip()
            if not q or q.startswith("#"):
                continue
            methods = []
            case_pass = True
            saw_verdict = False  # any method produced a non-empty Pass/Fail result
            for n in indices:
                mtype = (raw.get(f"testMethodType_{n}") or "").strip()
                result = (raw.get(f"result_{n}") or "").strip()
                if not mtype and not result:
                    continue  # this method column is absent for the row
                name = mtype or f"method_{n}"
                methods.append({
                    "type": name,
                    "result": result,  # empty == no verdict (timeout / no answer)
                    "passingScore": (raw.get(f"passingScore_{n}") or "").strip(),
                    "explanation": (raw.get(f"explanation_{n}") or "").strip(),
                })
                if result:
                    saw_verdict = True
                    if result.lower() != PASS:
                        case_pass = False
            # A case with no Pass/Fail verdict at all is an error/timeout, not a
            # fail: the agent produced nothing to grade.
            rows.append({
                "question": q,
                "expectedResponse": (raw.get("expectedResponse") or "").strip(),
                "actualResponse": (raw.get("actualResponse") or "").strip(),
                "methods": methods,
                "casePass": bool(saw_verdict and case_pass),
                "caseError": not saw_verdict,
            })
    return rows


def summarize(rows: list[dict]) -> dict:
    """Roll a list of normalized rows up into a summary + per-method tally."""
    method_tally: dict[str, dict[str, int]] = {}
    cases_passed = 0
    cases_error = 0
    for r in rows:
        if r["caseError"]:
            cases_error += 1
        elif r["casePass"]:
            cases_passed += 1
        for m in r["methods"]:
            tally = method_tally.setdefault(m["type"], {})
            if m["result"]:
                tally[m["result"]] = tally.get(m["result"], 0) + 1
            else:
                # empty result = the grader never ran (e.g. empty answer);
                # bucket as Error, kept out of the method's pass/fail denominator
                tally["Error"] = tally.get("Error", 0) + 1
    cases_total = len(rows)
    # Errors count in the total but are excluded from the pass-rate denominator.
    scored = cases_total - cases_error
    pass_rate = round(cases_passed / scored, 4) if scored else None
    return {
        "totalCases": cases_total,
        "scoredCases": scored,
        "passedCases": cases_passed,
        "failedCases": scored - cases_passed,
        "errorCases": cases_error,
        "passRate": pass_rate,
        "methods": method_tally,
    }


def merge_rows(file_rows: list[list[dict]]) -> list[dict]:
    """Merge several files' rows for one agent, dedup by question text.

    Files are processed in order; a later file's row for a given question wins,
    so re-running an agent and dropping the newer export overrides the older.
    First-seen order is preserved.
    """
    merged: dict[str, dict] = {}
    for rows in file_rows:
        for r in rows:
            merged[r["question"]] = r  # last write wins
    return list(merged.values())


def match_agent(file_stem: str, agents: list[dict]) -> dict | None:
    """Match a file to the agent whose (normalized) name is in the file name."""
    norm = re.sub(r"[^a-z0-9]+", " ", file_stem.lower())
    best, best_len = None, 0
    for a in agents:
        an = re.sub(r"[^a-z0-9]+", " ", a["name"].lower()).strip()
        if an and an in norm and len(an) > best_len:
            best, best_len = a, len(an)
    return best


def collect(files: list[Path], agents: list[dict], out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Group files by agent (or by file stem when unmatched). Several CSVs can map
    # to the same agent in one run; their rows are merged into one record.
    groups: dict[str, dict] = {}
    for path in files:
        agent = match_agent(path.stem, agents)
        slug = slugify(agent["name"]) if agent else slugify(path.stem)
        g = groups.setdefault(slug, {"agent": agent, "files": []})
        g["files"].append(path)

    collected = []
    for slug, g in groups.items():
        agent = g["agent"]
        paths = g["files"]
        rows = merge_rows([parse_rows(p) for p in paths])
        summary = summarize(rows)
        record = {
            "agent": agent["name"] if agent else None,
            "bot_id": agent["bot_id"] if agent else None,
            "source_files": [p.name for p in paths],
            "summary": summary,
            "rows": rows,
        }
        (out_dir / f"{slug}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        collected.append(record)
        tag = agent["name"] if agent else f"(unmatched: {slug})"
        merged = f"  [merged {len(paths)} files]" if len(paths) > 1 else ""
        print(f"  {tag}: {summary['passedCases']}/{summary['totalCases']} "
              f"passed  (passRate={summary['passRate']}){merged}", file=sys.stderr)
    return collected


def write_summaries(collected: list[dict], agents: list[dict], out_dir: Path,
                    run_label: str | None = None) -> None:
    # union of all method names for stable columns
    methods = sorted({m for r in collected for m in r["summary"]["methods"]})

    fields = ["agent", "bot_id", "source_files", "total", "scored", "passed",
              "failed", "errors", "pass_rate"]
    fields += [f"{m}" for m in methods]
    with (out_dir / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in collected:
            s = r["summary"]
            row = {
                "agent": r["agent"] or "",
                "bot_id": r["bot_id"] or "",
                "source_files": "; ".join(r["source_files"]),
                "total": s["totalCases"],
                "scored": s.get("scoredCases", s["totalCases"]),
                "passed": s["passedCases"],
                "failed": s["failedCases"],
                "errors": s.get("errorCases", 0),
                "pass_rate": s["passRate"] if s["passRate"] is not None else "",
            }
            for m in methods:
                t = s["methods"].get(m, {})
                row[m] = ",".join(f"{k}={v}" for k, v in sorted(t.items()))
            w.writerow(row)

    # note any agents from the README with no exported file
    matched = {r["agent"] for r in collected if r["agent"]}
    missing = [a["name"] for a in agents if a["name"] not in matched]

    (out_dir / "summary.json").write_text(json.dumps({
        "runLabel": run_label,
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "agents": [{
            "agent": r["agent"],
            "bot_id": r["bot_id"],
            "source_files": r["source_files"],
            "summary": r["summary"],
        } for r in collected],
        "missingAgents": missing,
    }, indent=2), encoding="utf-8")

    if missing:
        print(f"  note: no export matched README agents: {', '.join(missing)}",
              file=sys.stderr)


def process_run(run_label: str, files: list[Path], agents: list[dict],
                out_dir: Path) -> list[dict]:
    """Collect one run's CSVs into out_dir; return the collected records."""
    print(f"\n[{run_label}] collecting {len(files)} export(s) -> {rel(out_dir)}",
          file=sys.stderr)
    collected = collect(files, agents, out_dir)
    write_summaries(collected, agents, out_dir, run_label=run_label)
    return collected


def write_comparison(runs: dict[str, list[dict]], agents: list[dict],
                     root: Path) -> Path:
    """Write an agent x run pass-rate matrix across all runs."""
    labels = list(runs.keys())
    # index each run's results by agent name
    by_run = {lbl: {r["agent"]: r["summary"] for r in recs if r["agent"]}
              for lbl, recs in runs.items()}
    agent_names = [a["name"] for a in agents]
    # include any unmatched/extra agents seen in the data
    for recs in runs.values():
        for r in recs:
            if r["agent"] and r["agent"] not in agent_names:
                agent_names.append(r["agent"])

    comp_csv = root / "comparison.csv"
    with comp_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["agent"] + labels)
        for name in agent_names:
            cells = []
            for lbl in labels:
                s = by_run.get(lbl, {}).get(name)
                if s and s["passRate"] is not None:
                    cells.append(f"{s['passedCases']}/{s['totalCases']} "
                                 f"({s['passRate']*100:.0f}%)")
                else:
                    cells.append("")
            w.writerow([name] + cells)

    (root / "comparison.json").write_text(json.dumps({
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "runs": labels,
        "agents": {
            name: {lbl: by_run.get(lbl, {}).get(name) for lbl in labels}
            for name in agent_names
        },
    }, indent=2), encoding="utf-8")
    return comp_csv


def discover_runs(in_dir: Path, flat_label: str) -> dict[str, list[Path]]:
    """Map run-label -> CSVs. Subfolders are runs; loose CSVs become one run."""
    runs: dict[str, list[Path]] = {}
    for sub in sorted(p for p in in_dir.iterdir() if p.is_dir()):
        csvs = sorted(sub.glob("*.csv"))
        if csvs:
            runs[sub.name] = csvs
    flat = sorted(in_dir.glob("*.csv"))
    if flat:
        runs[flat_label] = flat
    return runs


def main() -> None:
    ap = argparse.ArgumentParser(description="Collect Copilot Studio Evaluate-tab CSV exports.")
    ap.add_argument("files", nargs="*", help="Explicit CSV files (default: scan --input-dir).")
    ap.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR),
                    help=f"Directory of exported CSVs; subfolders are treated as separate "
                         f"runs (default: {rel(DEFAULT_INPUT_DIR)}).")
    ap.add_argument("--run-name", default="default",
                    help="Run label for loose CSVs / explicit files (default: 'default').")
    ap.add_argument("--results-root", default=str(RESULTS_ROOT),
                    help=f"Root for output (default: {rel(RESULTS_ROOT)}).")
    args = ap.parse_args()

    agents = parse_agents()
    results_root = Path(args.results_root)

    if args.files:
        runs = {args.run_name: [Path(f) for f in args.files if Path(f).exists()]}
    else:
        in_dir = Path(args.input_dir)
        if not in_dir.exists():
            sys.exit(f"ERROR: input dir not found: {in_dir}\n"
                     f"Create it and drop the Evaluate-tab CSV exports there "
                     f"(optionally in per-run subfolders), or pass files explicitly.")
        runs = discover_runs(in_dir, args.run_name)
    runs = {lbl: fs for lbl, fs in runs.items() if fs}
    if not runs:
        sys.exit("ERROR: no CSV files found to collect.")

    collected_by_run: dict[str, list[dict]] = {}
    for label, files in runs.items():
        out_dir = results_root / slugify(label)
        collected_by_run[label] = process_run(label, files, agents, out_dir)

    print(f"\n=== Results ===")
    for label, collected in collected_by_run.items():
        print(f"[{label}]  -> {rel(results_root / slugify(label))}")
        for r in collected:
            s = r["summary"]
            name = r["agent"] or f"(unmatched: {'; '.join(r['source_files'])})"
            rate = f"{s['passRate']*100:.0f}%" if s["passRate"] is not None else "n/a"
            print(f"   {name:<40} {s['passedCases']:>3}/{s['totalCases']:<3} pass  ({rate})")

    if len(collected_by_run) > 1:
        comp = write_comparison(collected_by_run, agents, results_root)
        print(f"\nCross-run comparison: {rel(comp)} (+ comparison.json)")
    print(f"\nPer-run files: <run>/summary.csv, summary.json, <agent>.json")


if __name__ == "__main__":
    main()
