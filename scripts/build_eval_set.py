"""Build the 20-question evaluation test set for the MultiEURLEX Search Agent.

Two artifacts are produced from one source-of-truth table so they never drift:

1. multieurlex_eval_set_source.csv  - rich, human-reviewable. Holds the question,
   the precise expected answer, a behavioral rubric, the grounding document
   (celex_id + title), the metadata dimensions used to constrain/disambiguate,
   the difficulty tier, and (for tricky cases) the distractor doc ids that also
   look like candidate answers but are ruled out by metadata.

2. multieurlex_eval_set_copilot_import.csv - conforms to the Copilot Studio
   "Import conversations" template (data/eval/EvalConversationTemplate.csv):
   a leading block of '#' comment lines, then the columns
   conversationNumber, question, response. Each of the 20 questions is its own
   conversation (one Q&A pair) so the tricky cases never share context. The
   precise answer goes in the optional 'response' column (reference only; the
   agent reply is not compared against it).

Every answer is grounded in data/processed/multieurlex_selected_300.csv. For the
"tricky" tier, more than one document in the corpus plausibly answers the topical
question; the metadata stated in the question wording (year, document type,
domain, country, subject) rules out all but one. Copilot Studio passes ONLY the
question string to the agent, so the disambiguating metadata is woven into the
question text itself.

Template limits enforced here: <=500 characters per question, <=8 Q&A pairs per
conversation, <=50 conversations.
"""

import csv
import sys
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "processed" / "multieurlex_selected_300.csv"
OUT_DIR = ROOT / "data" / "eval"

# tier legend:
#   A = few metadata cues (broad topical question, one obvious matching doc)
#   B = medium metadata (typically 2 constraints, e.g. year + domain)
#   C = precise (3+ metadata constraints pinpoint a single doc)
#   D = tricky (several docs are candidate answers; metadata rules all but one out)
#
# fields per record:
#   id, tier, question, expected_answer, rubric,
#   source_celex_id, metadata_used, distractor_celex_ids, notes
RECORDS = [
    # ---------------- Tier A: few metadata cues ----------------
    dict(
        id="Q01", tier="A",
        question="Which EU act sets maximum residue levels for pesticides such as "
                 "acetamiprid and tebuconazole in or on certain products?",
        expected_answer="Commission Regulation (EU) 2015/401 of 25 February 2015, which "
                        "amends Annexes II and III to Regulation (EC) No 396/2005 on "
                        "maximum residue levels of pesticides.",
        rubric="Should identify Regulation (EU) 2015/401 and state that it amends the "
               "pesticide MRL Regulation (EC) No 396/2005.",
        source_celex_id="32015R0401",
        metadata_used="topic=pesticide MRLs",
        distractor_celex_ids="",
        notes="Single obvious topical match in the corpus.",
    ),
    dict(
        id="Q02", tier="A",
        question="Which EU act includes pyriproxyfen as an active substance for biocidal "
                 "products, and which Member State acted as Rapporteur for its evaluation?",
        expected_answer="Commission Directive 2013/5/EU of 14 February 2013, which adds "
                        "pyriproxyfen to Annex I of Directive 98/8/EC. The Netherlands was "
                        "the designated Rapporteur Member State.",
        rubric="Should identify Directive 2013/5/EU (amending Directive 98/8/EC on biocidal "
               "products) and name the Netherlands as Rapporteur Member State.",
        source_celex_id="32013L0005",
        metadata_used="topic=biocidal active substance",
        distractor_celex_ids="",
        notes="Answer requires a content fact (Rapporteur) from the document body.",
    ),
    dict(
        id="Q03", tier="A",
        question="Which EU regulation amended the rules on the single payment scheme and "
                 "support to vine-growers?",
        expected_answer="Regulation (EU) No 1028/2012 of the European Parliament and of the "
                        "Council of 25 October 2012, amending Council Regulation (EC) No "
                        "1234/2007 as regards the single payment scheme and support to "
                        "vine-growers.",
        rubric="Should identify Regulation (EU) No 1028/2012 and that it amends Regulation "
               "(EC) No 1234/2007 (Single CMO).",
        source_celex_id="32012R1028",
        metadata_used="topic=vine-growers / single payment scheme",
        distractor_celex_ids="",
        notes="Only document in corpus from the EP & Council on this topic.",
    ),
    dict(
        id="Q04", tier="A",
        question="Which EU regulation lays down the model for operational programmes under "
                 "the Investment for growth and jobs goal for the European Structural and "
                 "Investment Funds?",
        expected_answer="Commission Implementing Regulation (EU) No 288/2014 of 25 February "
                        "2014, adopted pursuant to Regulation (EU) No 1303/2013 (and "
                        "Regulation (EU) No 1299/2013 for cooperation programmes).",
        rubric="Should identify Implementing Regulation (EU) No 288/2014 and link it to the "
               "Common Provisions Regulation (EU) No 1303/2013.",
        source_celex_id="32014R0288",
        metadata_used="topic=operational programmes / ESI Funds",
        distractor_celex_ids="",
        notes="Broad topical cue, single match.",
    ),
    dict(
        id="Q05", tier="A",
        question="Which EU regulation authorised the use of methacrylate copolymers as food "
                 "additives in solid food supplements?",
        expected_answer="Commission Regulation (EU) No 816/2013 of 28 August 2013, amending "
                        "Annex II to Regulation (EC) No 1333/2008 on food additives.",
        rubric="Should identify Regulation (EU) No 816/2013 and that it amends the food "
               "additives Regulation (EC) No 1333/2008.",
        source_celex_id="32013R0816",
        metadata_used="topic=food additives / methacrylate copolymers",
        distractor_celex_ids="",
        notes="Single topical match.",
    ),

    # ---------------- Tier B: medium metadata (~2 constraints) ----------------
    dict(
        id="Q06", tier="B",
        question="What does the 2015 EU Decision concerning restrictive measures in view of "
                 "the situation in Libya change?",
        expected_answer="Council Decision (CFSP) 2015/382 of 6 March 2015 amends Decision "
                        "2011/137/CFSP, extending the criteria for the travel ban and asset "
                        "freeze measures (implementing UN Security Council Resolution 2174 "
                        "(2014)).",
        rubric="Should identify Council Decision (CFSP) 2015/382, that it amends Decision "
               "2011/137/CFSP, and that it concerns travel ban / asset freeze measures on Libya.",
        source_celex_id="32015D0382",
        metadata_used="year=2015; topic=Libya restrictive measures",
        distractor_celex_ids="",
        notes="Year + topic constrain to one CFSP decision.",
    ),
    dict(
        id="Q07", tier="B",
        question="Which 2013 Directive in the Trade domain postpones the transposition and "
                 "application dates of the Solvency II Directive?",
        expected_answer="Directive 2013/58/EU of the European Parliament and of the Council "
                        "of 11 December 2013, amending Directive 2009/138/EC (Solvency II) as "
                        "regards the dates of transposition, application and the repeal of "
                        "Solvency I directives.",
        rubric="Should identify Directive 2013/58/EU and that it amends the Solvency II "
               "Directive 2009/138/EC by postponing its dates.",
        source_celex_id="32013L0058",
        metadata_used="year=2013; document_type=Directive; domain=Trade",
        distractor_celex_ids="",
        notes="Year + type + domain.",
    ),
    dict(
        id="Q08", tier="B",
        question="Which 2015 Transport Directive updates the EU rules on port reception "
                 "facilities for ship-generated waste to reflect the revised MARPOL Annex V "
                 "garbage categories?",
        expected_answer="Commission Directive (EU) 2015/2087 of 18 November 2015, amending "
                        "Annex II to Directive 2000/59/EC on port reception facilities for "
                        "ship-generated waste and cargo residues.",
        rubric="Should identify Directive (EU) 2015/2087 and that it amends Annex II to "
               "Directive 2000/59/EC, reflecting the MARPOL Annex V categorisation of garbage.",
        source_celex_id="32015L2087",
        metadata_used="year=2015; document_type=Directive; domain=Transport",
        distractor_celex_ids="",
        notes="Year + type + domain.",
    ),
    dict(
        id="Q09", tier="B",
        question="Which 2014 EU Regulation lays down the rules on the information that "
                 "Member States must send under the European Maritime and Fisheries Fund?",
        expected_answer="Commission Implementing Regulation (EU) No 1243/2014 of 20 November "
                        "2014, adopted pursuant to Regulation (EU) No 508/2014 on the "
                        "European Maritime and Fisheries Fund.",
        rubric="Should identify Implementing Regulation (EU) No 1243/2014 and link it to the "
               "EMFF Regulation (EU) No 508/2014.",
        source_celex_id="32014R1243",
        metadata_used="year=2014; topic=European Maritime and Fisheries Fund",
        distractor_celex_ids="",
        notes="Year + topic.",
    ),
    dict(
        id="Q10", tier="B",
        question="Which 2014 EU Regulation amends Regulation (EU) No 965/2012 on the "
                 "technical requirements and administrative procedures for air operations?",
        expected_answer="Commission Regulation (EU) No 379/2014 of 7 April 2014, amending "
                        "Regulation (EU) No 965/2012 pursuant to the civil aviation "
                        "Regulation (EC) No 216/2008.",
        rubric="Should identify Regulation (EU) No 379/2014 and that it amends the air "
               "operations Regulation (EU) No 965/2012.",
        source_celex_id="32014R0379",
        metadata_used="year=2014; topic=air operations",
        distractor_celex_ids="",
        notes="Year + topic; long document.",
    ),

    # ---------------- Tier C: precise (3+ constraints) ----------------
    dict(
        id="Q11", tier="C",
        question="Which 2014 Commission Implementing Regulation in the Finance domain governs "
                 "the reimbursement of agricultural appropriations carried over from financial "
                 "year 2014, and what limit applies to that carry-over?",
        expected_answer="Commission Implementing Regulation (EU) No 1259/2014 of 24 November "
                        "2014. The carry-over is limited to 2% of the initial appropriations "
                        "(and to the amount of the direct-payments adjustment).",
        rubric="Should identify Implementing Regulation (EU) No 1259/2014 and state the 2% "
               "carry-over limit.",
        source_celex_id="32014R1259",
        metadata_used="year=2014; document_type=Regulation; domain=Finance; "
                      "topic=carry-over reimbursement",
        distractor_celex_ids="",
        notes="Multiple constraints + precise numeric fact (2%).",
    ),
    dict(
        id="Q12", tier="C",
        question="Which 2013 Council Regulation in the employment and working conditions "
                 "domain lays down the salary weightings for EU officials serving in third "
                 "countries, and for which periods?",
        expected_answer="Council Regulation (EU) No 679/2013 of 15 July 2013, setting the "
                        "weightings applicable from 1 July 2011 to 30 June 2012 and from "
                        "1 July 2012 to the remuneration of officials, temporary and contract "
                        "staff serving in third countries.",
        rubric="Should identify Regulation (EU) No 679/2013 and the two periods "
               "(1 Jul 2011-30 Jun 2012 and from 1 Jul 2012).",
        source_celex_id="32013R0679",
        metadata_used="year=2013; document_type=Regulation; domain=Employment and working "
                      "conditions; topic=staff weightings",
        distractor_celex_ids="",
        notes="Multiple constraints + precise dates.",
    ),
    dict(
        id="Q13", tier="C",
        question="A 2014 Commission Regulation in the Energy domain defines the criteria and "
                 "geographic ranges of 'highly biodiverse grassland'. Which two Directives' "
                 "biofuel sustainability provisions does it serve?",
        expected_answer="Commission Regulation (EU) No 1307/2014 of 8 December 2014. It serves "
                        "Article 7b(3)(c) of Directive 98/70/EC (quality of petrol and diesel "
                        "fuels) and Article 17(3)(c) of Directive 2009/28/EC (promotion of "
                        "energy from renewable sources).",
        rubric="Should identify Regulation (EU) No 1307/2014 and name both Directive 98/70/EC "
               "and Directive 2009/28/EC.",
        source_celex_id="32014R1307",
        metadata_used="year=2014; document_type=Regulation; domain=Energy; "
                      "topic=highly biodiverse grassland",
        distractor_celex_ids="",
        notes="Multiple constraints + two-part precise answer.",
    ),
    dict(
        id="Q14", tier="C",
        question="Which 2015 Directive amends Directive 94/62/EC to reduce the consumption "
                 "of lightweight plastic carrier bags, and what per-person consumption "
                 "targets does it set?",
        expected_answer="Directive (EU) 2015/720 of the European Parliament and of the "
                        "Council of 29 April 2015. Member States must ensure annual "
                        "consumption does not exceed 90 lightweight plastic carrier bags per "
                        "person by 31 December 2019 and 40 per person by 31 December 2025 (or "
                        "ensure such bags are not provided free of charge by 31 December 2018).",
        rubric="Should identify Directive (EU) 2015/720 and state the 90-bags-by-2019 and "
               "40-bags-by-2025 per-person targets.",
        source_celex_id="32015L0720",
        metadata_used="year=2015; document_type=Directive; domain=Trade; "
                      "topic=plastic carrier bags",
        distractor_celex_ids="",
        notes="Multiple constraints + precise numeric targets.",
    ),
    dict(
        id="Q15", tier="C",
        question="Which 2013 Commission Directive in the Law domain amends Annex III to the "
                 "rail interoperability Directive 2008/57/EC, and what concern does it add?",
        expected_answer="Commission Directive 2013/9/EU of 11 March 2013. It amends Annex III "
                        "to Directive 2008/57/EC to add an explicit reference to accessibility "
                        "for persons with disabilities and persons with reduced mobility.",
        rubric="Should identify Directive 2013/9/EU and that it adds accessibility for "
               "persons with disabilities / reduced mobility to Annex III of Directive 2008/57/EC.",
        source_celex_id="32013L0009",
        metadata_used="year=2013; document_type=Directive; domain=Law; "
                      "topic=rail interoperability accessibility",
        distractor_celex_ids="",
        notes="Multiple constraints + content fact.",
    ),

    # ---------------- Tier D: tricky (metadata disambiguates among candidates) ----------------
    dict(
        id="Q16", tier="D",
        question="In the Council and Commission Decision (EU, Euratom) on the EU position in "
                 "the Association Council established with Ukraine, which Article of the "
                 "Association Agreement provides for its provisional application?",
        expected_answer="Decision (EU, Euratom) 2015/60 (the Ukraine decision) refers to "
                        "Article 486 of the EU-Ukraine Association Agreement for provisional "
                        "application.",
        rubric="Should select the Ukraine decision (2015/60) and answer Article 486 - not the "
               "Moldova or Georgia decisions.",
        source_celex_id="32015D0060",
        metadata_used="country=Ukraine (disambiguator)",
        distractor_celex_ids="32015D0055 (Moldova, Art. 464); 32015D0054 (Georgia, Art. 431)",
        notes="Three near-identical Association Council decisions; country in question text "
              "selects the right one.",
    ),
    dict(
        id="Q17", tier="D",
        question="Two of the EU-third country Association Council decisions (EU, Euratom) "
                 "establishing Sub-Committees in Trade configuration are dated 17 November "
                 "2014. Which of those concerns Georgia, and what is its decision number?",
        expected_answer="Council and Commission Decision (EU, Euratom) 2015/54, which concerns "
                        "the Association Agreement with Georgia (dated 17 November 2014).",
        rubric="Should select the Georgia decision and give number 2015/54. The other "
               "17 November 2014 decision is Moldova (2015/55); Ukraine (2015/60) is dated "
               "15 December 2014 and must be excluded.",
        source_celex_id="32015D0054",
        metadata_used="date=17 November 2014 AND country=Georgia (disambiguators)",
        distractor_celex_ids="32015D0055 (Moldova, also 17 Nov 2014); "
                             "32015D0060 (Ukraine, 15 Dec 2014)",
        notes="Date narrows to two; country picks one. Ukraine is excluded by date.",
    ),
    dict(
        id="Q18", tier="D",
        question="Among the 2015 European Central Bank Decisions, which one concerns public "
                 "access to ECB documents (not the one on targeted longer-term refinancing "
                 "operations), and which earlier decision does it amend?",
        expected_answer="Decision (EU) 2015/529 of the ECB (ECB/2015/1) of 21 January 2015, "
                        "which amends Decision ECB/2004/3 on public access to ECB documents.",
        rubric="Should select the public-access decision (ECB/2015/1, Decision 2015/529) and "
               "state it amends ECB/2004/3 - not the TLTRO decision.",
        source_celex_id="32015D0001",
        metadata_used="subject=public access to documents (disambiguator)",
        distractor_celex_ids="32015D0005 (ECB/2015/5, Decision 2015/299, on TLTROs)",
        notes="Two 2015 ECB Finance decisions; subject in question text disambiguates.",
    ),
    dict(
        id="Q19", tier="D",
        question="In the 2015 European Central Bank Decision on targeted longer-term "
                 "refinancing operations, what spread was eliminated and over which period "
                 "were the affected operations to be conducted?",
        expected_answer="Decision (EU) 2015/299 of the ECB (ECB/2015/5) of 10 February 2015 "
                        "eliminated the 10 basis points spread over the main refinancing "
                        "operations rate for the TLTROs to be conducted between March 2015 "
                        "and June 2016.",
        rubric="Should select the TLTRO decision (ECB/2015/5) and state the 10 basis points "
               "spread and the March 2015-June 2016 period - not the public-access decision.",
        source_celex_id="32015D0005",
        metadata_used="subject=targeted longer-term refinancing operations (disambiguator)",
        distractor_celex_ids="32015D0001 (ECB/2015/1, Decision 2015/529, on public access)",
        notes="Pairs with Q18; subject disambiguates and answer carries precise figures.",
    ),
    dict(
        id="Q20", tier="D",
        question="The corpus contains several 2013-2015 measures that add or restrict "
                 "chemical substances. Which one is the 2015 Delegated Directive that adds "
                 "substances to the list of restricted substances in electrical and "
                 "electronic equipment (RoHS), and name two substances it adds?",
        expected_answer="Commission Delegated Directive (EU) 2015/863 of 31 March 2015, which "
                        "amends Annex II to RoHS Directive 2011/65/EU. It adds, among others, "
                        "DEHP (Bis(2-ethylhexyl) phthalate), BBP (Butyl benzyl phthalate), "
                        "DBP (Dibutyl phthalate) and HBCDD.",
        rubric="Should select Delegated Directive (EU) 2015/863 (RoHS, Directive 2011/65/EU) "
               "and name at least two of DEHP, BBP, DBP, HBCDD - not the pesticide MRL "
               "Regulation or the biocidal-products Directive.",
        source_celex_id="32015L0863",
        metadata_used="year=2015; document_type=Delegated Directive; "
                      "subject=RoHS / electrical and electronic equipment (disambiguators)",
        distractor_celex_ids="32015R0401 (pesticide MRLs, also 2015, 'substances'); "
                             "32013L0005 (biocidal active substance pyriproxyfen)",
        notes="Three 'substances' documents; RoHS/EEE subject + Delegated Directive type "
              "disambiguate.",
    ),
]


def load_titles():
    titles = {}
    with CORPUS.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            titles[r["celex_id"]] = r["title"]
    return titles


def main():
    titles = load_titles()
    # validate every grounding doc exists in the corpus
    missing = [r["source_celex_id"] for r in RECORDS if r["source_celex_id"] not in titles]
    if missing:
        raise SystemExit(f"Grounding docs not found in corpus: {missing}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1) rich source-of-truth file
    source_path = OUT_DIR / "multieurlex_eval_set_source.csv"
    fieldnames = [
        "id", "tier", "question", "expected_answer", "rubric",
        "source_celex_id", "source_title", "metadata_used",
        "distractor_celex_ids", "notes",
    ]
    with source_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in RECORDS:
            row = dict(r)
            row["source_title"] = titles[r["source_celex_id"]]
            w.writerow(row)

    # 2) Copilot Studio "Import conversations" file. Matches the layout of
    #    data/eval/EvalConversationTemplate.csv: a block of '#' comment lines,
    #    then conversationNumber, question, response. One conversation per
    #    question keeps the tricky cases context-independent.
    import_path = OUT_DIR / "multieurlex_eval_set_copilot_import.csv"
    header_comments = [
        "# Import conversations to test your agent.",
        "#",
        "# Limitations",
        "# - 8 question-and-answer pairs max per conversation.",
        "# - 50 conversations max.",
        "# - 500 characters max per question, including spaces.",
        "#",
        "# Imported columns",
        "# conversationNumber - Identifies each conversation. All questions and "
        "responses with the same conversation number will run as a single test "
        "case against the agent.",
        "# question - The user prompt that the agent will respond to.",
        "# response - The reference agent reply. This field is optional. The agent "
        "response isn't compared to this reference answer.",
        "#",
        "# Test methods",
        "# - Test methods are not included in this template. You can select them "
        "after importing the test cases.",
        "# - By default, the 'General quality' test method is added to the "
        "imported test set.",
        "#",
        "# For more details, refer to the documentation: "
        "https://go.microsoft.com/fwlink/?linkid=2335991",
        "#",
    ]
    if len(RECORDS) > 50:
        raise SystemExit(f"Too many conversations: {len(RECORDS)} (max 50)")
    with import_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        for line in header_comments:
            w.writerow([line])
        w.writerow(["conversationNumber", "question", "response"])
        for i, r in enumerate(RECORDS, start=1):
            q = r["question"]
            if len(q) > 500:
                raise SystemExit(f"{r['id']} question exceeds 500 chars ({len(q)})")
            w.writerow([str(i), q, r["expected_answer"]])

    print(f"Wrote {source_path} ({len(RECORDS)} rows)")
    print(f"Wrote {import_path} ({len(RECORDS)} rows)")
    # tier summary
    from collections import Counter
    tiers = Counter(r["tier"] for r in RECORDS)
    print("Tier distribution:", dict(sorted(tiers.items())))


if __name__ == "__main__":
    main()
