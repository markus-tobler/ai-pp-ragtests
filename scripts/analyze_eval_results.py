#!/usr/bin/env python3
"""Static analysis of evaluation results -> charts + a factual markdown report.

Reads the roll-up `summary.json` files produced by `collect_eval_results.py`
(one per run directory under data/eval/results/) and renders charts comparing
agents against each other and across runs. The accompanying markdown only states
bare facts read from the data (counts, pass rates, per-method tallies, sample
sizes, missing agents) and links the charts; it makes no recommendations.

Data layout consumed (one run = one sub-directory of the results root):

    data/eval/results/
        <run-label>/
            summary.json      # authoritative roll-up, schema below
            <agent-slug>.json # per-agent rows (optional, not required here)

    summary.json:
        { runLabel, generatedUtc,
          agents: [ { agent, bot_id, source_file,
                      summary: { totalCases, scoredCases, passedCases, failedCases,
                                 errorCases, passRate,
                                 methods: { <Method>: { Pass, Fail, Error } } } } ],
          missingAgents: [ ... ] }

    Pass/fail is scored on one method only (default CompareMeaning). "Error" cases
    are timeouts/empty answers the grader could not score: counted in the absolute
    totals but excluded from the pass-rate denominator.

Output (default data/eval/analysis/):
    charts/*.png    # one PNG per chart
    report.md       # factual tables + embedded chart links

Usage:
    python3 scripts/analyze_eval_results.py
    python3 scripts/analyze_eval_results.py --results-dir <dir> --output-dir <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: write PNGs, never open a window
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RESULTS_DIR = REPO_ROOT / "data" / "eval" / "results"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "eval" / "analysis"

# Common prefix stripped from agent names for compact chart labels only;
# full names are always kept in tables.
LABEL_STRIP_PREFIX = "MultiEURLEX Classic "

PASS_COLOR = "#2e7d32"
FAIL_COLOR = "#c62828"
ERROR_COLOR = "#f9a825"  # amber: timeout / no answer to grade

# Eval method used to decide whether a case passed/failed for the headline
# pass-rate chart, passed/failed chart, and the failing-question analysis.
# Other methods (e.g. GeneralQuality) are still shown in the per-method chart.
DEFAULT_SCORE_METHOD = "CompareMeaning"


def rel(p: Path) -> str:
    """Repo-relative path for display, or absolute if outside the repo."""
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def short_label(agent: str) -> str:
    """Compact label for chart axes."""
    return agent[len(LABEL_STRIP_PREFIX):] if agent.startswith(LABEL_STRIP_PREFIX) else agent


# --------------------------------------------------------------------------- #
# Load
# --------------------------------------------------------------------------- #


def load_runs(results_dir: Path) -> list[dict]:
    """Load every run's summary.json, sorted by generatedUtc then label.

    Returns a list of run dicts (the parsed summary.json plus a `_path` key).
    """
    runs: list[dict] = []
    for summary_path in sorted(results_dir.glob("*/summary.json")):
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  ! skipping {rel(summary_path)}: {exc}", file=sys.stderr)
            continue
        data["_path"] = summary_path
        data.setdefault("runLabel", summary_path.parent.name)
        runs.append(data)

    def sort_key(r: dict) -> tuple[str, str]:
        return (r.get("generatedUtc") or "", r.get("runLabel") or "")

    runs.sort(key=sort_key)
    return runs


def all_methods(runs: list[dict]) -> list[str]:
    """Sorted union of every eval-method name seen across all runs."""
    methods: set[str] = set()
    for run in runs:
        for a in run.get("agents", []):
            methods.update((a.get("summary") or {}).get("methods", {}).keys())
    return sorted(methods)


def all_agents(runs: list[dict]) -> list[str]:
    """Sorted union of agent names across all runs (preserves coverage facts)."""
    agents: set[str] = set()
    for run in runs:
        for a in run.get("agents", []):
            agents.add(a.get("agent", "?"))
    return sorted(agents)


def method_pass_rate(method_tally: dict[str, int]) -> float | None:
    """Pass / (Pass + Fail) for one method, or None when no cases."""
    p = method_tally.get("Pass", 0)
    f = method_tally.get("Fail", 0)
    total = p + f
    return p / total if total else None


def score_counts(agent_summary: dict, method: str) -> tuple[int, int, int, int, int]:
    """(pass, fail, error, scored, total) for `method` from an agent's tally.

    `error` = cases the grader could not score (empty result / timeout); these are
    excluded from `scored` (the pass-rate denominator) but kept in `total`.
    Falls back to summary-level errorCases when the method tally has no Error key.
    """
    t = agent_summary.get("methods", {}).get(method, {})
    p = t.get("Pass", 0)
    f = t.get("Fail", 0)
    e = t.get("Error", agent_summary.get("errorCases", 0))
    scored = p + f
    return p, f, e, scored, scored + e


def load_run_rows(run: dict) -> list[dict]:
    """Read the per-agent `<slug>.json` files sitting beside a run's summary.json.

    Each returned dict is one agent's parsed file: {agent, rows: [...], ...}.
    A case row carries `methods: [{type, result}]`; a case is counted as passed
    only when every method result is "Pass" (matches the summary's passedCases).
    """
    summary_path: Path = run["_path"]
    out: list[dict] = []
    for jp in sorted(summary_path.parent.glob("*.json")):
        if jp.name == "summary.json":
            continue
        try:
            out.append(json.loads(jp.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  ! skipping {rel(jp)}: {exc}", file=sys.stderr)
    return out


def aggregate_question_failures(run: dict,
                                score_method: str = DEFAULT_SCORE_METHOD) -> list[dict]:
    """Aggregate case rows by question text across all agents in one run.

    Scoring uses only `score_method` (default CompareMeaning); other methods are
    ignored here. A case fails when that method's result is "Fail".

    Returns a list (one entry per distinct question) of:
        { question, expected, asked_by, fail_count, error_count,
          cells: { (agent, score_method): "Pass"|"Fail"|"Error" } }
    `asked_by` = how many agents had this question; `fail_count` = agents whose
    case failed (verdict "Fail"); `error_count` = agents where the grader could
    not score it (timeout / empty answer) — counted but never treated as a fail.
    Sorted by fail_count desc, then error_count desc.
    """
    agg: dict[str, dict] = {}
    for agent_file in load_run_rows(run):
        agent = agent_file.get("agent", "?")
        for row in agent_file.get("rows", []):
            q = (row.get("question") or "").strip()
            if not q:
                continue
            result = next((m.get("result", "") for m in row.get("methods", [])
                           if m.get("type") == score_method), None)
            if result is None:
                continue  # this agent wasn't scored on the chosen method
            state = "Pass" if result == "Pass" else ("Fail" if result == "Fail"
                                                      else "Error")
            entry = agg.setdefault(q, {
                "question": q,
                "expected": (row.get("expectedResponse") or "").strip(),
                "asked_by": 0,
                "fail_count": 0,
                "error_count": 0,
                "cells": {},
            })
            entry["asked_by"] += 1
            entry["cells"][(agent, score_method)] = state
            if state == "Fail":
                entry["fail_count"] += 1
            elif state == "Error":
                entry["error_count"] += 1

    return sorted(agg.values(),
                  key=lambda e: (e["fail_count"], e["error_count"]), reverse=True)


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #


def save(fig, out_dir: Path, name: str) -> str:
    """Write a figure to <out_dir>/charts/<name>.png; return its name."""
    charts_dir = out_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(charts_dir / f"{name}.png", dpi=130)
    plt.close(fig)
    return name


def chart_passrate_by_agent(run: dict, out_dir: Path,
                            score_method: str = DEFAULT_SCORE_METHOD) -> str:
    """Bar: pass rate per agent (scored on score_method), annotated passed/total."""
    agents = run.get("agents", [])
    labels = [short_label(a["agent"]) for a in agents]
    counts = [score_counts(a["summary"], score_method) for a in agents]
    # pass rate over scored cases only (errors excluded from the denominator)
    rates = [(p / scored * 100) if scored else 0 for p, _f, _e, scored, _t in counts]

    fig, ax = plt.subplots(figsize=(max(6, len(agents) * 1.6), 4.5))
    bars = ax.bar(labels, rates, color="#1565c0")
    for bar, (p, _f, e, scored, _t) in zip(bars, counts):
        note = f"{p}/{scored}"
        if e:
            note += f"\n({e} err excl.)"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            note,
            ha="center", va="bottom", fontsize=8,
        )
    ax.set_ylim(0, 110)
    ax.set_ylabel("Pass rate (%)")
    ax.set_title(f"Case pass rate by agent ({score_method}, errors excluded) — "
                 f"run '{run.get('runLabel')}'")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.autofmt_xdate(rotation=20)
    return save(fig, out_dir, f"passrate_by_agent__{run.get('runLabel')}")


def chart_passfail_stacked(run: dict, out_dir: Path,
                           score_method: str = DEFAULT_SCORE_METHOD) -> str:
    """Stacked bar: passed vs failed case counts per agent (scored on method)."""
    agents = run.get("agents", [])
    labels = [short_label(a["agent"]) for a in agents]
    counts = [score_counts(a["summary"], score_method) for a in agents]
    passed = [p for p, _f, _e, _s, _t in counts]
    failed = [f for _p, f, _e, _s, _t in counts]
    errored = [e for _p, _f, e, _s, _t in counts]

    fig, ax = plt.subplots(figsize=(max(6, len(agents) * 1.6), 4.5))
    ax.bar(labels, passed, color=PASS_COLOR, label="Pass")
    ax.bar(labels, failed, bottom=passed, color=FAIL_COLOR, label="Fail")
    bottom_pf = [p + f for p, f in zip(passed, failed)]
    ax.bar(labels, errored, bottom=bottom_pf, color=ERROR_COLOR,
           label="Error (timeout)")
    for i, (_p, _f, _e, _s, t) in enumerate(counts):
        ax.text(i, t + 0.3, str(t), ha="center", fontsize=9)
    ax.set_ylabel("Cases")
    ax.set_title(f"Passed / failed / error cases by agent ({score_method}) — "
                 f"run '{run.get('runLabel')}'")
    ax.legend()
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.autofmt_xdate(rotation=20)
    return save(fig, out_dir, f"passfail_stacked__{run.get('runLabel')}")


def chart_method_passrate(run: dict, methods: list[str], out_dir: Path) -> str:
    """Grouped bar: per-method pass rate per agent within one run."""
    agents = run.get("agents", [])
    labels = [short_label(a["agent"]) for a in agents]
    n = len(agents)
    width = 0.8 / max(1, len(methods))

    fig, ax = plt.subplots(figsize=(max(6, n * 1.9), 4.5))
    for mi, method in enumerate(methods):
        rates = []
        for a in agents:
            tally = a["summary"].get("methods", {}).get(method, {})
            r = method_pass_rate(tally)
            rates.append((r * 100) if r is not None else 0)
        xs = [i + mi * width for i in range(n)]
        ax.bar(xs, rates, width=width, label=method)

    ax.set_xticks([i + width * (len(methods) - 1) / 2 for i in range(n)])
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylim(0, 105)
    ax.set_ylabel("Pass rate (%)")
    ax.set_title(f"Per-method pass rate by agent — run '{run.get('runLabel')}'")
    ax.legend(title="Eval method")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    return save(fig, out_dir, f"method_passrate__{run.get('runLabel')}")


def chart_passrate_across_runs(runs: list[dict], agents: list[str], out_dir: Path,
                               score_method: str = DEFAULT_SCORE_METHOD) -> str:
    """Grouped bar: each agent's pass rate (scored on method) across runs (x=run)."""
    run_labels = [r.get("runLabel") for r in runs]
    n = len(runs)
    width = 0.8 / max(1, len(agents))

    fig, ax = plt.subplots(figsize=(max(7, n * 2.2), 4.8))
    for ai, agent in enumerate(agents):
        rates = []
        for run in runs:
            match = next((a for a in run.get("agents", []) if a["agent"] == agent), None)
            if match:
                p, _f, _e, scored, _t = score_counts(match["summary"], score_method)
                rates.append(p / scored * 100 if scored else 0)
            else:
                rates.append(0)
        xs = [i + ai * width for i in range(n)]
        ax.bar(xs, rates, width=width, label=short_label(agent))

    ax.set_xticks([i + width * (len(agents) - 1) / 2 for i in range(n)])
    ax.set_xticklabels(run_labels, rotation=15, ha="right")
    ax.set_ylim(0, 105)
    ax.set_ylabel("Pass rate (%)")
    ax.set_title(f"Agent pass rate across runs ({score_method})")
    ax.legend(title="Agent", fontsize=8)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    return save(fig, out_dir, "passrate_across_runs")


def chart_top_failures(run: dict, ranked: list[dict], out_dir: Path,
                       top_n: int = 10,
                       score_method: str = DEFAULT_SCORE_METHOD) -> str | None:
    """Heatmap: top-N failing questions (rows) x agent (cols), scored on method.

    Cell colour: green=Pass, red=Fail, amber=Error/timeout, grey=not asked of
    that agent. Shows questions with at least one failure or error.
    """
    top = [e for e in ranked
           if e["fail_count"] > 0 or e.get("error_count", 0) > 0][:top_n]
    if not top:
        return None

    # Stable column order: (agent, method) pairs actually present, grouped by agent.
    cols: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for e in top:
        for key in e["cells"]:
            if key not in seen:
                seen.add(key)
    for agent in sorted({a for a, _ in seen}):
        for method in sorted({m for a, m in seen if a == agent}):
            cols.append((agent, method))

    # 0 = not asked (grey), 1 = Pass (green), 2 = Fail (red), 3 = Error (amber)
    import numpy as np
    from matplotlib.colors import ListedColormap

    state_code = {None: 0, "Pass": 1, "Fail": 2, "Error": 3}
    grid = np.zeros((len(top), len(cols)))
    for ri, e in enumerate(top):
        for ci, key in enumerate(cols):
            grid[ri, ci] = state_code.get(e["cells"].get(key), 0)

    cmap = ListedColormap(["#cfd8dc", PASS_COLOR, FAIL_COLOR, ERROR_COLOR])

    fig_h = max(3.5, 0.55 * len(top) + 1.5)
    fig_w = max(7, 1.1 * len(cols) + 4)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.imshow(grid, cmap=cmap, vmin=0, vmax=3, aspect="auto")

    col_labels = [short_label(a) for a, _ in cols]
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(col_labels, fontsize=8, rotation=20, ha="right")
    ax.set_yticks(range(len(top)))

    def _ylab(i: int, e: dict) -> str:
        tag = f"{e['fail_count']}✗"
        if e.get("error_count"):
            tag += f" {e['error_count']}E"
        return f"#{i+1} ({tag}) " + textwrap_one(e["question"], 56)
    ax.set_yticklabels([_ylab(i, e) for i, e in enumerate(top)], fontsize=8)

    # mark cells for legibility in print / greyscale
    for ri in range(len(top)):
        for ci in range(len(cols)):
            if grid[ri, ci] == 2:
                ax.text(ci, ri, "✗", ha="center", va="center",
                        color="white", fontsize=9)
            elif grid[ri, ci] == 3:
                ax.text(ci, ri, "E", ha="center", va="center",
                        color="black", fontsize=9)

    ax.set_title(f"Top {len(top)} failing questions ({score_method}) — "
                 f"where they fail (run '{run.get('runLabel')}')")
    # legend
    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(facecolor=FAIL_COLOR, label="Fail ✗"),
        Patch(facecolor=ERROR_COLOR, label="Error/timeout (E)"),
        Patch(facecolor=PASS_COLOR, label="Pass"),
        Patch(facecolor="#cfd8dc", label="not asked"),
    ], bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8, frameon=False)
    return save(fig, out_dir, f"top_failures__{run.get('runLabel')}")


def textwrap_one(s: str, width: int) -> str:
    """Single-line truncation with an ellipsis for tidy y-axis labels."""
    s = " ".join(s.split())
    return s if len(s) <= width else s[: width - 1] + "…"


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #


def fmt_pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.1f}%"


def write_report(runs: list[dict], methods: list[str], agents: list[str],
                 chart_names: dict, failures: dict, out_dir: Path,
                 top_n: int = 10,
                 score_method: str = DEFAULT_SCORE_METHOD) -> Path:
    """Emit report.md with factual tables and links to the charts.

    `failures` maps run label -> {"chart": <name|None>, "ranked": [...]}.
    Headline pass/fail uses `score_method`; per-method tallies are kept too.
    """
    lines: list[str] = []
    a = lines.append

    a("# Evaluation Results — Static Analysis")
    a("")
    a(f"_Generated {datetime.now().isoformat(timespec='seconds')} from "
      f"`{rel(DEFAULT_RESULTS_DIR)}`._")
    a("")
    a(f"Runs analyzed: **{len(runs)}** · agents seen: **{len(agents)}** · "
      f"eval methods: {', '.join(f'`{m}`' for m in methods) or '—'}.")
    a("")
    a(f"**Pass/fail scoring uses the `{score_method}` method only**; other "
      "methods are reported per-method for reference but do not affect the "
      "headline pass rate, the passed/failed counts, or the failing-question "
      "analysis.")
    a("")
    a("**Errors (timeouts).** Cases where the agent returned nothing to grade "
      "(empty response) are counted as errors, shown in the absolute counts, but "
      "excluded from the pass-rate denominator — pass rate = passed / (passed + "
      "failed), errors not in the divisor.")
    a("")
    a("This report restates the numbers in the result files; it draws no "
      "conclusions. Note that agents do not all share the same case count, so "
      "pass rates compare proportions over different sample sizes.")
    a("")

    # ----- Cross-run section ------------------------------------------------ #
    if len(runs) > 1:
        a("## Across runs")
        a("")
        a(f"![Agent pass rate across runs](charts/{chart_names['across_runs']}.png)")
        a("")
        header = "| Agent | " + " | ".join(r.get("runLabel") for r in runs) + " |"
        sep = "|" + "---|" * (len(runs) + 1)
        a(header)
        a(sep)
        for agent in agents:
            cells = []
            for run in runs:
                m = next((x for x in run.get("agents", []) if x["agent"] == agent), None)
                if m:
                    p, _f, e, scored, _t = score_counts(m["summary"], score_method)
                    rate = p / scored if scored else None
                    cell = f"{fmt_pct(rate)} ({p}/{scored})"
                    if e:
                        cell += f" +{e}E"
                    cells.append(cell)
                else:
                    cells.append("absent")
            a(f"| {agent} | " + " | ".join(cells) + " |")
        a("")

    # ----- Per-run sections ------------------------------------------------- #
    for run in runs:
        label = run.get("runLabel")
        a(f"## Run: {label}")
        a("")
        meta = []
        if run.get("generatedUtc"):
            meta.append(f"generated `{run['generatedUtc']}`")
        if run.get("_path"):
            meta.append(f"source `{rel(run['_path'])}`")
        if meta:
            a("_" + " · ".join(meta) + "_")
            a("")

        cn = chart_names["per_run"][label]
        a(f"![Pass rate by agent](charts/{cn['passrate']}.png)")
        a("")
        a(f"![Passed vs failed cases](charts/{cn['passfail']}.png)")
        a("")
        a(f"![Per-method pass rate](charts/{cn['method']}.png)")
        a("")

        # Per-agent fact table. Headline Passed/Failed/Error/Pass-rate use
        # score_method; trailing columns give every method's own tally.
        head = (f"| Agent | Cases | Passed ({score_method}) | Failed | Errors | "
                "Pass rate | " + " | ".join(methods) + " |")
        a(head)
        a("|" + "---|" * (6 + len(methods)))
        for ag in run.get("agents", []):
            s = ag["summary"]
            p, f, e, scored, total = score_counts(s, score_method)
            rate = p / scored if scored else None
            mcells = []
            for m in methods:
                mt = s.get("methods", {}).get(m, {})
                r = method_pass_rate(mt)
                if r is None:
                    mcells.append("—")
                else:
                    err = mt.get("Error", 0)
                    suffix = f" +{err}E" if err else ""
                    mcells.append(f"{fmt_pct(r)} ({mt.get('Pass',0)}/"
                                  f"{mt.get('Pass',0)+mt.get('Fail',0)}){suffix}")
            a(f"| {ag['agent']} | {total} | {p} | {f} | {e} | "
              f"{fmt_pct(rate)} | " + " | ".join(mcells) + " |")
        a("")

        missing = run.get("missingAgents") or []
        if missing:
            a(f"**Agents with no result in this run:** {', '.join(missing)}.")
            a("")

        # ----- Top failing questions ---------------------------------------- #
        fdata = failures.get(label, {})
        ranked = [e for e in fdata.get("ranked", [])
                  if e["fail_count"] > 0 or e.get("error_count", 0) > 0]
        if ranked:
            top = ranked[:top_n]
            a(f"### Top {len(top)} failing questions")
            a("")
            if fdata.get("chart"):
                a(f"![Top failing questions heatmap](charts/{fdata['chart']}.png)")
                a("")
            a(f"Ranked by number of agents whose `{score_method}` check failed "
              "(then by errors). Errors (timeouts) are listed separately and are "
              "not counted as failures.")
            a("")
            a("| # | Question | Asked by | Failed | Failing agents | Errored agents |")
            a("|---|---|---|---|---|---|")
            for i, e in enumerate(top, 1):
                fails = [short_label(ag) for (ag, _m), res in sorted(e["cells"].items())
                         if res == "Fail"]
                errs = [short_label(ag) for (ag, _m), res in sorted(e["cells"].items())
                        if res == "Error"]
                q = textwrap_one(e["question"], 90).replace("|", "\\|")
                a(f"| {i} | {q} | {e['asked_by']} | "
                  f"{e['fail_count']}/{e['asked_by']} | {', '.join(fails) or '—'} | "
                  f"{', '.join(errs) or '—'} |")
            a("")

    out_path = out_dir / "report.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR,
                    help=f"root holding <run>/summary.json (default {rel(DEFAULT_RESULTS_DIR)})")
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                    help=f"where charts/ and report.md are written (default {rel(DEFAULT_OUTPUT_DIR)})")
    ap.add_argument("--top-n", type=int, default=10,
                    help="how many most-failing questions to chart/table (default 10)")
    ap.add_argument("--score-method", default=DEFAULT_SCORE_METHOD,
                    help="eval method used to decide pass/fail for the headline "
                         f"charts and failing-question analysis (default {DEFAULT_SCORE_METHOD})")
    args = ap.parse_args(argv)

    if not args.results_dir.is_dir():
        print(f"error: results dir not found: {args.results_dir}", file=sys.stderr)
        return 2

    runs = load_runs(args.results_dir)
    if not runs:
        print(f"error: no <run>/summary.json under {args.results_dir}", file=sys.stderr)
        return 2

    methods = all_methods(runs)
    agents = all_agents(runs)
    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    sm = args.score_method
    if sm not in methods:
        print(f"  warning: score method '{sm}' not present in data "
              f"(methods: {methods}); pass/fail counts may be empty.", file=sys.stderr)
    print(f"Loaded {len(runs)} run(s), {len(agents)} agent(s), methods: {methods}; "
          f"scoring on '{sm}'")

    chart_names: dict = {"per_run": {}}
    failures: dict = {}
    for run in runs:
        label = run.get("runLabel")
        chart_names["per_run"][label] = {
            "passrate": chart_passrate_by_agent(run, out_dir, score_method=sm),
            "passfail": chart_passfail_stacked(run, out_dir, score_method=sm),
            "method": chart_method_passrate(run, methods, out_dir),
        }
        ranked = aggregate_question_failures(run, score_method=sm)
        fail_chart = chart_top_failures(run, ranked, out_dir, top_n=args.top_n,
                                        score_method=sm)
        failures[label] = {"chart": fail_chart, "ranked": ranked}
        n_failing = sum(1 for e in ranked if e["fail_count"] > 0)
        print(f"  charts for run '{label}' written "
              f"({n_failing} distinct failing question(s))")

    if len(runs) > 1:
        chart_names["across_runs"] = chart_passrate_across_runs(
            runs, agents, out_dir, score_method=sm)
        print("  cross-run chart written")

    report = write_report(runs, methods, agents, chart_names, failures, out_dir,
                          top_n=args.top_n, score_method=sm)
    print(f"Report: {rel(report)}")
    print(f"Charts: {rel(out_dir / 'charts')}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
