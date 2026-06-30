#!/usr/bin/env python3
"""
Build the RAG test corpus from MultiEURLEX (Implementation Plan, Phases 1-3).

Phase 1  Load MultiEURLEX, parse CELEX, filter by length (600-3000 words).
Phase 2  Derive 5 controlled metadata dimensions.
Phase 3  Stratified selection of exactly 300 documents (100 short/medium/long).

Install dependencies:
    pip install datasets huggingface_hub

Usage:
    python scripts/02_data_select_corpus.py
    python scripts/02_data_select_corpus.py --lang en --seed 42
"""

import argparse
import csv
import io
import json
import random
import re
import statistics
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

WORDS_PER_PAGE = 300
MIN_WORDS = 600          # ~2 pages
MAX_WORDS = 3000         # ~10 pages
TARGET_TOTAL = 300
PER_LEVEL = 100          # short / medium / long

LENGTH_LEVELS = {                  # (min_words, max_words) inclusive lower, exclusive upper
    "short":  (600, 1200),         # 2-4 pages
    "medium": (1200, 2100),        # 4-7 pages
    "long":   (2100, 3001),        # 7-10 pages
}

SPLIT = "test"
SPLIT_FILE = {"train": "train.jsonl", "test": "test.jsonl", "validation": "dev.jsonl"}

OUT_DIR = Path("data/processed")
REPORT_DIR = Path("reports")

# ---------------------------------------------------------------------------
# Phase 2 controlled vocabularies
# ---------------------------------------------------------------------------

# EUROVOC level-1 domain id -> policy_domain  (source: eurovoc, 21 values)
EUROVOC_L1 = {
    "100142": "Politics",
    "100143": "International relations",
    "100144": "European Union",
    "100145": "Law",
    "100146": "Economics",
    "100147": "Trade",
    "100148": "Finance",
    "100149": "Social questions",
    "100150": "Education and communications",
    "100151": "Science",
    "100152": "Business and competition",
    "100153": "Employment and working conditions",
    "100154": "Transport",
    "100155": "Environment",
    "100156": "Agriculture, forestry and fisheries",
    "100157": "Agri-foodstuffs",
    "100158": "Production, technology and research",
    "100159": "Energy",
    "100160": "Industry",
    "100161": "Geography",
    "100162": "International organisations",
    "100163": "Political framework",
}

# CELEX sector code -> name  (source: celex)
SECTORS = {
    "0": "Consolidated Texts", "1": "Treaties", "2": "International Agreements",
    "3": "EU Legislation", "4": "Supplementary Legislation", "5": "Preparatory Acts",
    "6": "Case Law (CJEU)", "7": "National Transposition", "8": "National Case Law",
    "9": "Parliamentary Questions", "C": "Other OJ-C Documents", "E": "EFTA Documents",
}

# CELEX document-type code -> document_type  (source: celex)
DOC_TYPES = {
    "R": "Regulation", "L": "Directive", "D": "Decision", "A": "Agreement",
    "F": "Framework Decision", "E": "Common Position", "H": "Recommendation",
    "DC": "Delegated Regulation", "PC": "Commission Proposal",
    "SC": "Staff Working Document", "AC": "Advisory Committee Opinion",
    "XC": "Communication (OJ-C)",
}

# year_band thresholds  (source: celex, derived)
YEAR_BANDS = [
    (0, 1979, "1950-1979"), (1980, 1989, "1980-1989"), (1990, 1999, "1990-1999"),
    (2000, 2009, "2000-2009"), (2010, 2014, "2010-2014"), (2015, 2019, "2015-2019"),
    (2020, 9999, "2020-2026"),
]

# rule-based keyword maps (source: rule_based). First match wins (ordered).
LEGAL_ACTOR_RULES = [
    ("National court",       r"\b(court of justice|national court|tribunal|court of appeal)\b"),
    ("Financial institution",r"\b(central bank|credit institution|bank|insurer|investment firm)\b"),
    ("Member state authority",r"\b(member state|national authority|competent authorit|national government)\b"),
    ("Public agency",        r"\b(agency|authority|office|board|commission)\b"),
    ("Company",              r"\b(undertaking|company|enterprise|business|manufacturer)\b"),
    ("Employer",             r"\b(employer|workplace|occupational)\b"),
    ("Worker",               r"\b(worker|employee|staff|labour)\b"),
    ("Consumer/citizen",     r"\b(consumer|citizen|individual|natural person)\b"),
    ("Non-EU country",       r"\b(third country|non-member|non-eu)\b"),
    ("International organization", r"\b(united nations|world trade|international organi[sz]ation|wto)\b"),
    ("EU institution",       r"\b(european parliament|european commission|council of|european union)\b"),
]

APPLICABLE_ROLE_RULES = [
    ("Importer/exporter",     r"\b(import|export|customs|tariff)\b"),
    ("Operator",              r"\b(operator|installation|plant|facility)\b"),
    ("Supplier",              r"\b(supplier|provider|distributor|trader)\b"),
    ("Data subject",          r"\b(personal data|data subject|privacy|data protection)\b"),
    ("Financial intermediary",r"\b(intermediary|investment|securities|portfolio)\b"),
    ("Beneficiary",           r"\b(beneficiary|grant|subsidy|aid recipient|funding)\b"),
    ("Applicant",             r"\b(applicant|application|request for|apply for)\b"),
    ("Competent authority",   r"\b(competent authority|supervis|enforcement|inspection)\b"),
    ("Employee",              r"\b(employee|worker|staff)\b"),
    ("Employer",              r"\b(employer)\b"),
    ("Consumer",              r"\b(consumer|end-user)\b"),
    ("Public body",           r"\b(public body|public authority|administration)\b"),
    ("Regulated entity",      r"\b(shall comply|obligation|requirement|subject to)\b"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_celex(celex: str) -> dict:
    """Parse CELEX: SECTOR + YEAR(4) + DOCTYPE(1-2) + NUMBER."""
    if not celex or not celex[1:5].isdigit():
        return {}
    tail = celex[5:]
    dt_code = ""
    for ch in tail:
        if ch.isalpha():
            dt_code += ch
        else:
            break
    return {
        "sector": SECTORS.get(celex[0], f"Unknown ({celex[0]})"),
        "year": int(celex[1:5]),
        "doc_type": DOC_TYPES.get(dt_code, "Other"),
        "dt_code": dt_code,
    }


def year_band(year: int) -> str:
    for lo, hi, label in YEAR_BANDS:
        if lo <= year <= hi:
            return label
    return "Other"


def length_level(word_count: int) -> str:
    for level, (lo, hi) in LENGTH_LEVELS.items():
        if lo <= word_count < hi:
            return level
    return ""


def match_rule(text: str, rules) -> str:
    low = text.lower()
    for label, pattern in rules:
        if re.search(pattern, low):
            return label
    return "Other"


def policy_domain(labels: list) -> str:
    for lid in labels:
        if str(lid) in EUROVOC_L1:
            return EUROVOC_L1[str(lid)]
    return "Other"


# ---------------------------------------------------------------------------
# Phase 1 — load + filter
# ---------------------------------------------------------------------------

def load_candidates(lang: str) -> list:
    from huggingface_hub import hf_hub_download

    print(f"Loading MultiEURLEX ({lang}, {SPLIT})...")
    zip_path = hf_hub_download(
        repo_id="nlpaueb/multi_eurlex",
        filename="multi_eurlex_translated.zip",
        repo_type="dataset",
    )

    candidates, seen = [], set()
    with zipfile.ZipFile(zip_path) as zf, zf.open(SPLIT_FILE[SPLIT]) as f:
        for line in io.TextIOWrapper(f, encoding="utf-8"):
            data = json.loads(line)
            text = data["text"].get(lang)
            celex = data["celex_id"]
            if not text or not celex or celex in seen:
                continue
            parsed = parse_celex(celex)
            if not parsed:
                continue
            wc = len(text.split())
            if not (MIN_WORDS <= wc <= MAX_WORDS):
                continue
            seen.add(celex)
            labels = data["eurovoc_concepts"]["level_1"]
            candidates.append({
                "celex_id": celex,
                "title": text.split("\n", 1)[0][:200].strip(),
                "language": lang,
                "document_text": text,
                "word_count": wc,
                "page_estimate": round(wc / WORDS_PER_PAGE, 1),
                "length_level": length_level(wc),
                "policy_domain": policy_domain(labels),
                "document_type": parsed["doc_type"],
                "year": parsed["year"],
                "year_band": year_band(parsed["year"]),
                "legal_actor_type": match_rule(text, LEGAL_ACTOR_RULES),
                "applicable_role": match_rule(text, APPLICABLE_ROLE_RULES),
                "metadata_json": json.dumps({
                    "sector": parsed["sector"],
                    "dt_code": parsed["dt_code"],
                    "eurovoc_level_1": labels,
                    "metadata_source": {
                        "policy_domain": "eurovoc",
                        "document_type": "celex",
                        "year_band": "celex",
                        "legal_actor_type": "rule_based",
                        "applicable_role": "rule_based",
                    },
                }, ensure_ascii=False),
                "source_dataset": "MultiEURLEX",
                "source_split": SPLIT,
                "selection_batch": "ragtest-001",
            })
    print(f"  {len(candidates)} candidates after length filter "
          f"({MIN_WORDS}-{MAX_WORDS} words).")
    return candidates


# ---------------------------------------------------------------------------
# Phase 3 — stratified, balanced selection
# ---------------------------------------------------------------------------

BALANCE_DIMS = ("policy_domain", "document_type", "year_band")


def select_balanced(candidates: list, seed: int) -> list:
    rng = random.Random(seed)
    by_level = defaultdict(list)
    for doc in candidates:
        if doc["length_level"]:
            by_level[doc["length_level"]].append(doc)

    selected = []
    for level in ("short", "medium", "long"):
        pool = by_level[level][:]
        rng.shuffle(pool)
        target = min(PER_LEVEL, len(pool))
        counts = {dim: Counter() for dim in BALANCE_DIMS}
        picked = []
        # greedily pick the candidate that least increases skew
        for _ in range(target):
            best, best_score = None, None
            for doc in pool:
                score = sum(counts[dim][doc[dim]] for dim in BALANCE_DIMS)
                if best_score is None or score < best_score:
                    best, best_score = doc, score
            picked.append(best)
            pool.remove(best)
            for dim in BALANCE_DIMS:
                counts[dim][best[dim]] += 1
        if target < PER_LEVEL:
            print(f"  WARNING: only {target} '{level}' docs available (< {PER_LEVEL}).")
        selected.extend(picked)
    return selected


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

CSV_FIELDS = [
    "celex_id", "title", "language", "document_text", "word_count", "page_estimate",
    "length_level", "policy_domain", "document_type", "year", "year_band",
    "legal_actor_type", "applicable_role", "metadata_json",
    "source_dataset", "source_split", "selection_batch",
]


def export(selected: list):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    jsonl_path = OUT_DIR / "multieurlex_selected_300.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for doc in selected:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    csv_path = OUT_DIR / "multieurlex_selected_300.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(selected)

    write_report(selected)
    print(f"\nWrote:\n  {jsonl_path}\n  {csv_path}\n  {REPORT_DIR/'selection_summary.md'}")


def write_report(selected: list):
    n = len(selected)
    wc = [d["word_count"] for d in selected]
    lines = ["# Selection Summary", "",
             f"- Total documents: **{n}**",
             f"- Word count: min {min(wc)}, max {max(wc)}, "
             f"mean {statistics.mean(wc):.0f}, median {statistics.median(wc):.0f}",
             f"- Unique celex_id: {len(set(d['celex_id'] for d in selected))}", ""]

    dims = ["length_level", "policy_domain", "document_type",
            "year_band", "legal_actor_type", "applicable_role"]
    for dim in dims:
        counter = Counter(d[dim] for d in selected)
        lines.append(f"## {dim}  ({len(counter)} values)")
        for value, count in counter.most_common():
            lines.append(f"- {value}: {count}")
        lines.append("")

    (REPORT_DIR / "selection_summary.md").write_text("\n".join(lines), encoding="utf-8")

    # acceptance checks
    print("\nAcceptance checks:")
    checks = {
        "exactly 300 rows": n == TARGET_TOTAL,
        "all have text": all(d["document_text"] for d in selected),
        "no duplicate celex_id": len(set(d["celex_id"] for d in selected)) == n,
        "all 2-10 pages": all(2 <= d["page_estimate"] <= 10.1 for d in selected),
    }
    for dim in dims[1:]:
        k = len(set(d[dim] for d in selected))
        checks[f"{dim}: 5-20 distinct values ({k})"] = 5 <= k <= 20
    for label, ok in checks.items():
        print(f"  [{'OK' if ok else 'FAIL'}] {label}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", default="en", choices=["en", "de", "fr"])
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    candidates = load_candidates(args.lang)
    selected = select_balanced(candidates, args.seed)
    print(f"Selected {len(selected)} documents.")
    export(selected)


if __name__ == "__main__":
    main()
