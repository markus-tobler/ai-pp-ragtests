"""Build the 40-question evaluation test set for the MultiEURLEX Search Agent.

Two artifacts are produced from one source-of-truth table so they never drift:

1. multieurlex_eval_set_source.csv  - rich, human-reviewable. Holds the question,
   the precise expected answer, a behavioral rubric, the grounding document
   (celex_id + title), the metadata dimensions used to constrain/disambiguate,
   the difficulty tier, and (for tricky cases) the distractor doc ids that also
   look like candidate answers but are ruled out by metadata.

   The set holds 40 questions: 35 are grounded in a single corpus document and
   5 (tier E) are deliberately NOT answerable from the corpus - the expected
   behaviour there is for the agent to state that the available documents do
   not precisely answer the question (and to invent no CELEX id).

2. multieurlex_eval_set_copilot_import_conversation.csv - conforms to the
   Copilot Studio "Import conversations" template
   (data/eval/EvalConversationTemplate.csv): a leading block of '#' comment
   lines, then columns conversationNumber, question, response. Each of the 20
   questions is its own conversation (one Q&A pair) so the tricky cases never
   share context. The precise answer goes in the optional 'response' column
   (reference only; the agent reply is not compared against it).

3. multieurlex_eval_set_copilot_import_classic.csv - conforms to the Copilot
   Studio "classic" single-response template
   (data/eval/EvaluationTemplate_classic.csv): '#' comment lines, then columns
   question, expectedResponse. Here expectedResponse IS used by the match /
   similarity / compare-meaning test methods, so the precise answer goes there.

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
#   E = unanswerable (no corpus doc answers; agent must say so, invent no CELEX)
#
# fields per record:
#   id, tier, question, expected_answer, rubric,
#   source_celex_id, metadata_used, distractor_celex_ids, notes
#   unanswerable=True marks a tier-E record: source_celex_id is empty and the
#   expected_answer is the stand-alone "documents do not precisely answer"
#   statement (no CELEX prefix is added).
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

    # ================= EXPANSION: Q21-Q40 =================

    # ---------------- Tier A: few metadata cues ----------------
    dict(
        id="Q21", tier="A",
        question="Which EU act amends the rules protecting groundwater against pollution "
                 "and deterioration by updating the annex on threshold values for "
                 "pollutants?",
        expected_answer="Commission Directive 2014/80/EU of 20 June 2014, which amends "
                        "Annex II to Directive 2006/118/EC on the protection of groundwater "
                        "against pollution and deterioration.",
        rubric="Should identify Directive 2014/80/EU and that it amends Annex II to the "
               "groundwater Directive 2006/118/EC.",
        source_celex_id="32014L0080",
        metadata_used="topic=groundwater protection",
        distractor_celex_ids="",
        notes="Single topical match.",
    ),
    dict(
        id="Q22", tier="A",
        question="Which EU directive amends the Council Directive relating to honey, "
                 "notably clarifying the status of pollen?",
        expected_answer="Directive 2014/63/EU of the European Parliament and of the Council "
                        "of 15 May 2014, amending Council Directive 2001/110/EC relating to "
                        "honey.",
        rubric="Should identify Directive 2014/63/EU and that it amends the honey Directive "
               "2001/110/EC.",
        source_celex_id="32014L0063",
        metadata_used="topic=honey",
        distractor_celex_ids="",
        notes="Single topical match.",
    ),
    dict(
        id="Q23", tier="A",
        question="Which EU directive approximates Member States' laws on caseins and "
                 "caseinates intended for human consumption and repeals an older 1983 "
                 "directive?",
        expected_answer="Directive (EU) 2015/2203 of the European Parliament and of the "
                        "Council of 25 November 2015 on caseins and caseinates intended for "
                        "human consumption, repealing Council Directive 83/417/EEC.",
        rubric="Should identify Directive (EU) 2015/2203 and that it repeals Directive "
               "83/417/EEC.",
        source_celex_id="32015L2203",
        metadata_used="topic=caseins and caseinates",
        distractor_celex_ids="",
        notes="Single topical match.",
    ),
    dict(
        id="Q24", tier="A",
        question="Which EU regulation codifies the common rules for exports of goods from "
                 "the Union?",
        expected_answer="Regulation (EU) 2015/479 of the European Parliament and of the "
                        "Council of 11 March 2015 on common rules for exports (codification).",
        rubric="Should identify Regulation (EU) 2015/479 on common rules for exports.",
        source_celex_id="32015R0479",
        metadata_used="topic=common rules for exports",
        distractor_celex_ids="",
        notes="Single topical match (codification).",
    ),

    # ---------------- Tier B: medium metadata (~2 constraints) ----------------
    dict(
        id="Q25", tier="B",
        question="Which 2015 Council Directive in the Finance domain adds a common minimum "
                 "anti-abuse rule to the parent-subsidiary taxation Directive 2011/96/EU?",
        expected_answer="Council Directive (EU) 2015/121 of 27 January 2015, amending "
                        "Directive 2011/96/EU on the common system of taxation applicable to "
                        "parent companies and subsidiaries of different Member States by "
                        "adding a common anti-abuse rule.",
        rubric="Should identify Council Directive (EU) 2015/121 and that it adds an "
               "anti-abuse rule to Directive 2011/96/EU.",
        source_celex_id="32015L0121",
        metadata_used="year=2015; document_type=Directive; domain=Finance",
        distractor_celex_ids="",
        notes="Year + type + domain pinpoint a single doc.",
    ),
    dict(
        id="Q26", tier="B",
        question="Which 2013 Directive in the Trade domain amends the batteries Directive "
                 "2006/66/EC as regards placing on the market of portable batteries "
                 "containing cadmium and button cells containing mercury?",
        expected_answer="Directive 2013/56/EU of the European Parliament and of the Council "
                        "of 20 November 2013, amending Directive 2006/66/EC on batteries and "
                        "accumulators as regards the placing on the market of portable "
                        "batteries containing cadmium (cordless power tools) and button cells "
                        "with low mercury content.",
        rubric="Should identify Directive 2013/56/EU and that it amends the batteries "
               "Directive 2006/66/EC.",
        source_celex_id="32013L0056",
        metadata_used="year=2013; document_type=Directive; domain=Trade; topic=batteries",
        distractor_celex_ids="32013L0007 (biocidal active substance); "
                             "32013L0058 (Solvency II dates)",
        notes="Year+type+domain match three Trade Directives; battery topic disambiguates.",
    ),
    dict(
        id="Q27", tier="B",
        question="Which 2014 Regulation in the Transport domain amends the EU Emissions "
                 "Trading System Directive 2003/87/EC to limit aviation ETS coverage to "
                 "flights within the European Economic Area (the 'stop the clock' approach)?",
        expected_answer="Regulation (EU) No 421/2014 of the European Parliament and of the "
                        "Council of 16 April 2014, amending Directive 2003/87/EC, in view of "
                        "the implementation by 2020 of an international agreement and pending "
                        "that, limiting the EU ETS to flights within the EEA.",
        rubric="Should identify Regulation (EU) No 421/2014 and that it amends the EU ETS "
               "Directive 2003/87/EC for aviation.",
        source_celex_id="32014R0421",
        metadata_used="year=2014; document_type=Regulation; domain=Transport; topic=aviation ETS",
        distractor_celex_ids="32014R0716 (other 2014 Transport Regulation)",
        notes="Year+type+domain; aviation-ETS topic narrows to one.",
    ),
    dict(
        id="Q28", tier="B",
        question="Which 2015 Council Directive lays down the calculation methods and "
                 "reporting requirements for the greenhouse-gas intensity of petrol and "
                 "diesel fuels under the fuel quality Directive 98/70/EC?",
        expected_answer="Council Directive (EU) 2015/652 of 20 April 2015, laying down "
                        "calculation methods and reporting requirements pursuant to Article "
                        "7a of Directive 98/70/EC relating to the quality of petrol and "
                        "diesel fuels.",
        rubric="Should identify Council Directive (EU) 2015/652 and link it to the fuel "
               "quality Directive 98/70/EC.",
        source_celex_id="32015L0652",
        metadata_used="year=2015; document_type=Directive; topic=fuel quality / GHG intensity",
        distractor_celex_ids="",
        notes="Year + type + topic.",
    ),
    dict(
        id="Q29", tier="B",
        question="Which 2014 Regulation amends Regulation (EC) No 539/2001 on the visa "
                 "lists, and which third country does it move to the visa-exempt list?",
        expected_answer="Regulation (EU) No 259/2014 of the European Parliament and of the "
                        "Council of 3 April 2014, amending Regulation (EC) No 539/2001 by "
                        "transferring the Republic of Moldova to the visa-exempt Annex II "
                        "(for holders of biometric passports).",
        rubric="Should identify Regulation (EU) No 259/2014 and name the Republic of "
               "Moldova as moved to visa-free travel.",
        source_celex_id="32014R0259",
        metadata_used="year=2014; document_type=Regulation; domain=Geography; topic=visa lists",
        distractor_celex_ids="",
        notes="Year + type + domain pinpoint a single doc; answer carries a content fact.",
    ),
    dict(
        id="Q30", tier="B",
        question="Which 2015 Regulation (codification) in the Law domain sets out the "
                 "measures the Union may take following a report adopted by the WTO Dispute "
                 "Settlement Body on anti-dumping and anti-subsidy matters?",
        expected_answer="Regulation (EU) 2015/476 of the European Parliament and of the "
                        "Council of 11 March 2015 on the measures that the Union may take "
                        "following a report adopted by the WTO Dispute Settlement Body "
                        "concerning anti-dumping and anti-subsidy matters (codification).",
        rubric="Should identify Regulation (EU) 2015/476 and the WTO-DSB anti-dumping / "
               "anti-subsidy subject.",
        source_celex_id="32015R0476",
        metadata_used="year=2015; document_type=Regulation; domain=Law; topic=WTO DSB measures",
        distractor_celex_ids="",
        notes="Year + type + domain + topic.",
    ),

    # ---------------- Tier C: precise (3+ constraints) ----------------
    dict(
        id="Q31", tier="C",
        question="Which 2013 Council Directive (Euratom) in the Science domain lays down "
                 "requirements protecting the health of the general public regarding "
                 "radioactive substances in water intended for human consumption, and which "
                 "radionuclides does it bring into scope?",
        expected_answer="Council Directive 2013/51/Euratom of 22 October 2013. It sets "
                        "parametric values and monitoring for radioactive substances in "
                        "drinking water, including radon, tritium and an indicative dose.",
        rubric="Should identify Directive 2013/51/Euratom and mention radioactive substances "
               "in drinking water (radon / tritium / indicative dose).",
        source_celex_id="32013L0051",
        metadata_used="year=2013; document_type=Directive; domain=Science; "
                      "topic=radioactive substances in water",
        distractor_celex_ids="",
        notes="Multiple constraints + content fact; only Science Directive of 2013.",
    ),
    dict(
        id="Q32", tier="C",
        question="Which 2015 Commission Directive in the Trade domain adds a specific limit "
                 "value for formamide to Appendix C of the toy safety Directive 2009/48/EC?",
        expected_answer="Commission Directive (EU) 2015/2115 of 23 November 2015, amending "
                        "Appendix C to Annex II to Directive 2009/48/EC on the safety of toys "
                        "to adopt a specific limit value for formamide.",
        rubric="Should identify Directive (EU) 2015/2115 and that it sets a formamide limit "
               "value under the toy safety Directive 2009/48/EC.",
        source_celex_id="32015L2115",
        metadata_used="year=2015; document_type=Directive; domain=Trade; topic=toy safety / formamide",
        distractor_celex_ids="32015L0863 (RoHS substances); 32015L0720 (plastic bags)",
        notes="Several 2015 Trade Directives; formamide/toy-safety subject disambiguates.",
    ),
    dict(
        id="Q33", tier="C",
        question="Which 2015 CFSP Decision appoints the European Union Special "
                 "Representative for Central Asia, who is appointed, and until when?",
        expected_answer="Council Decision (CFSP) 2015/598 of 15 April 2015 appoints Mr Peter "
                        "Burian as the EU Special Representative for Central Asia until "
                        "30 April 2016.",
        rubric="Should identify Decision (CFSP) 2015/598, name Peter Burian, and give the "
               "end date 30 April 2016.",
        source_celex_id="32015D0598",
        metadata_used="year=2015; document_type=Decision; domain=Geography; "
                      "topic=EUSR Central Asia",
        distractor_celex_ids="",
        notes="Many 2015 CFSP Geography decisions; EUSR-Central-Asia subject + name/date.",
    ),

    # ---------------- Tier D: tricky (metadata disambiguates among candidates) ----------------
    dict(
        id="Q34", tier="D",
        question="Two 2014 Regulations adjust the remuneration and pensions of EU officials "
                 "- one with effect from 1 July 2011 and one from 1 July 2012. Which applies "
                 "from 1 July 2012, and what adjustment percentage does it set?",
        expected_answer="Regulation (EU) No 423/2014 of 16 April 2014 adjusts remuneration "
                        "and pensions with effect from 1 July 2012, setting an adjustment of "
                        "0,8 %. (The 1 July 2011 adjustment, set at 0 %, is Regulation (EU) "
                        "No 422/2014.)",
        rubric="Should select Regulation (EU) No 423/2014 (1 July 2012, 0,8 %) - not "
               "Regulation (EU) No 422/2014 (1 July 2011, 0 %).",
        source_celex_id="32014R0423",
        metadata_used="effective_date=1 July 2012 (disambiguator)",
        distractor_celex_ids="32014R0422 (1 July 2011, 0 %)",
        notes="Two near-identical staff-pay Regulations; effective date + percentage pick one.",
    ),
    dict(
        id="Q35", tier="D",
        question="Several 2013 Directives add active substances to the biocidal products "
                 "Directive 98/8/EC. Which one includes Alkyl (C12-16) dimethylbenzyl "
                 "ammonium chloride as a wood-preservative (product-type 8) active substance, "
                 "and which Member State was Rapporteur?",
        expected_answer="Commission Directive 2013/7/EU of 21 February 2013 adds Alkyl "
                        "(C12-16) dimethylbenzyl ammonium chloride to Annex I of Directive "
                        "98/8/EC for product-type 8 (wood preservatives). Italy was the "
                        "Rapporteur Member State.",
        rubric="Should select Directive 2013/7/EU (Alkyl (C12-16) dimethylbenzyl ammonium "
               "chloride, PT8) and name Italy as Rapporteur - not the pyriproxyfen Directive.",
        source_celex_id="32013L0007",
        metadata_used="substance=Alkyl (C12-16) dimethylbenzyl ammonium chloride (disambiguator)",
        distractor_celex_ids="32013L0005 (pyriproxyfen, NL); 32013L0044 (other 98/8 substance)",
        notes="Several 98/8/EC active-substance Directives; substance name picks the right one.",
    ),

    # ---------------- Tier E: unanswerable (no corpus doc answers precisely) ----------------
    dict(
        id="Q36", tier="E", unanswerable=True,
        question="Which act in the corpus sets out the data subject's right to erasure (the "
                 "'right to be forgotten') of personal data?",
        expected_answer="The corpus contains no data-protection instrument; no document "
                        "establishes a right to erasure / 'right to be forgotten'. The agent "
                        "should state that the available documents do not precisely answer "
                        "this question and should not invent a CELEX id.",
        rubric="Should recognise that no corpus document covers data-protection / right to "
               "erasure and explicitly say the documents do not precisely answer; must not "
               "fabricate a CELEX id.",
        source_celex_id="",
        metadata_used="topic=data protection (absent from corpus)",
        distractor_celex_ids="",
        notes="No GDPR / data-protection act in the corpus.",
    ),
    dict(
        id="Q37", tier="E", unanswerable=True,
        question="Which 2015 Regulation sets the CO2 emission performance standards for new "
                 "passenger cars or light commercial vehicles?",
        expected_answer="No Regulation in the corpus sets CO2 emission performance standards "
                        "for cars or vans (the standard-setting Regulations 443/2009 and "
                        "510/2011 are not present; only a few Decisions approve eco-innovations "
                        "under that regime). The agent should state that the available "
                        "documents do not precisely answer this question.",
        rubric="Should recognise that no corpus Regulation sets car/van CO2 standards and say "
               "the documents do not precisely answer; eco-innovation Decisions are not a "
               "valid answer.",
        source_celex_id="",
        metadata_used="year=2015; document_type=Regulation (no matching topic in corpus)",
        distractor_celex_ids="32015D0295; 32014D0770 (eco-innovation Decisions referencing "
                             "the car-CO2 regime)",
        notes="Tempting CO2/eco-innovation Decisions exist, but no standard-setting Regulation.",
    ),
    dict(
        id="Q38", tier="E", unanswerable=True,
        question="In Regulation (EU) No 421/2014 amending the EU Emissions Trading System "
                 "for aviation, what per-tonne CO2 price applies to flights to and from third "
                 "countries?",
        expected_answer="Regulation (EU) No 421/2014 sets no per-tonne CO2 price; it limits "
                        "the aviation ETS to flights within the EEA and exempts (defers) "
                        "extra-EEA flights, rather than fixing a price. The agent should state "
                        "that the document does not precisely answer this question.",
        rubric="Should recognise that 421/2014 fixes no carbon price (it scopes the ETS to "
               "intra-EEA flights) and say the document does not precisely answer; must not "
               "invent a figure.",
        source_celex_id="",
        metadata_used="year=2014; document_type=Regulation; domain=Transport "
                      "(doc present, asked fact absent)",
        distractor_celex_ids="32014R0421 (the aviation-ETS Regulation, but it states no price)",
        notes="Anchor doc is in corpus but contains no such price.",
    ),
    dict(
        id="Q39", tier="E", unanswerable=True,
        question="Among the Directives that add active substances to the biocidal products "
                 "Directive 98/8/EC, which one adds glyphosate, and for which product-type?",
        expected_answer="No corpus Directive adds glyphosate to Directive 98/8/EC; the "
                        "98/8/EC amending Directives in the corpus add other substances "
                        "(e.g. pyriproxyfen, Alkyl (C12-16) dimethylbenzyl ammonium "
                        "chloride). The agent should state that the available documents do "
                        "not precisely answer this question.",
        rubric="Should recognise that no corpus biocidal Directive concerns glyphosate and "
               "say the documents do not precisely answer; must not map it onto another "
               "substance's Directive.",
        source_celex_id="",
        metadata_used="substance=glyphosate (absent from corpus)",
        distractor_celex_ids="32013L0005 (pyriproxyfen); 32013L0007 (Alkyl ammonium chloride)",
        notes="Plausible biocidal-substance pattern, but glyphosate is not in any corpus doc.",
    ),
    dict(
        id="Q40", tier="E", unanswerable=True,
        question="What total euro budget does Decision No 1386/2013/EU (the General Union "
                 "Environment Action Programme to 2020) allocate to each Member State?",
        expected_answer="Decision No 1386/2013/EU sets out priority objectives for the 7th "
                        "Environment Action Programme; it allocates no euro budget to Member "
                        "States. The agent should state that the document does not precisely "
                        "answer this question.",
        rubric="Should recognise that the 7th EAP is a priority-objectives programme with no "
               "per-Member-State budget figure and say the document does not precisely answer.",
        source_celex_id="",
        metadata_used="year=2013; document_type=Decision; domain=Finance "
                      "(doc present, asked fact absent)",
        distractor_celex_ids="32013D1386 (the 7th EAP, but it states no such budget)",
        notes="Anchor doc is in corpus but is non-budgetary.",
    ),
]

# Human-readable metadata filter block per question. Only the metadata that the
# question text actually constrains is listed; each label/value uses the exact
# corpus value so it maps straight onto a Dataverse WHERE clause. Tier A carries
# no filters (few metadata cues). For Tier D the listed filters deliberately
# match MORE than one document - the non-metadata disambiguator (country, date,
# subject) stays in the prose, which is what makes those cases tricky.
FILTERS = {
    # Tier A - none (broad topical)
    "Q01": [], "Q02": [], "Q03": [], "Q04": [], "Q05": [],
    # Tier B
    "Q06": [("Year", "2015"), ("Document type", "Decision")],
    "Q07": [("Year", "2013"), ("Document type", "Directive"), ("Policy domain", "Trade")],
    "Q08": [("Year", "2015"), ("Document type", "Directive"), ("Policy domain", "Transport")],
    "Q09": [("Year", "2014"), ("Document type", "Regulation")],
    "Q10": [("Year", "2014"), ("Document type", "Regulation")],
    # Tier C
    "Q11": [("Year", "2014"), ("Document type", "Regulation"), ("Policy domain", "Finance")],
    "Q12": [("Year", "2013"), ("Document type", "Regulation"),
            ("Policy domain", "Employment and working conditions")],
    "Q13": [("Year", "2014"), ("Document type", "Regulation"), ("Policy domain", "Energy")],
    "Q14": [("Year", "2015"), ("Document type", "Directive"), ("Policy domain", "Trade")],
    "Q15": [("Year", "2013"), ("Document type", "Directive"), ("Policy domain", "Law")],
    # Tier D - filters match several candidates; prose disambiguates
    "Q16": [("Year", "2015"), ("Document type", "Decision"), ("Policy domain", "Politics")],
    "Q17": [("Year", "2015"), ("Document type", "Decision"), ("Policy domain", "Politics")],
    "Q18": [("Year", "2015"), ("Document type", "Decision"), ("Policy domain", "Finance"),
            ("Legal actor type", "Financial institution")],
    "Q19": [("Year", "2015"), ("Document type", "Decision"), ("Policy domain", "Finance"),
            ("Legal actor type", "Financial institution")],
    "Q20": [("Year", "2015"), ("Document type", "Directive")],
    # --- Expansion: Tier A (none) ---
    "Q21": [], "Q22": [], "Q23": [], "Q24": [],
    # --- Tier B ---
    "Q25": [("Year", "2015"), ("Document type", "Directive"), ("Policy domain", "Finance")],
    "Q26": [("Year", "2013"), ("Document type", "Directive"), ("Policy domain", "Trade")],
    "Q27": [("Year", "2014"), ("Document type", "Regulation"), ("Policy domain", "Transport")],
    "Q28": [("Year", "2015"), ("Document type", "Directive")],
    "Q29": [("Year", "2014"), ("Document type", "Regulation"), ("Policy domain", "Geography")],
    "Q30": [("Year", "2015"), ("Document type", "Regulation"), ("Policy domain", "Law")],
    # --- Tier C ---
    "Q31": [("Year", "2013"), ("Document type", "Directive"), ("Policy domain", "Science")],
    "Q32": [("Year", "2015"), ("Document type", "Directive"), ("Policy domain", "Trade")],
    "Q33": [("Year", "2015"), ("Document type", "Decision"), ("Policy domain", "Geography")],
    # --- Tier D - filters match several candidates; prose disambiguates ---
    "Q34": [("Year", "2014"), ("Document type", "Regulation"),
            ("Policy domain", "Employment and working conditions")],
    "Q35": [("Year", "2013"), ("Document type", "Directive")],
    # --- Tier E - unanswerable. Filters narrow to candidate docs that look
    #     relevant but do not actually answer (or to an empty set). ---
    "Q36": [],
    "Q37": [("Year", "2015"), ("Document type", "Regulation")],
    "Q38": [("Year", "2014"), ("Document type", "Regulation"), ("Policy domain", "Transport")],
    "Q39": [("Year", "2013"), ("Document type", "Directive")],
    "Q40": [("Year", "2013"), ("Document type", "Decision"), ("Policy domain", "Finance")],
}


def render_question(record):
    """Question prose followed by a human-readable metadata filter block."""
    q = record["question"]
    filters = FILTERS.get(record["id"], [])
    if not filters:
        return q
    block = "\n".join(f"- {label}: {value}" for label, value in filters)
    return f"{q}\n\nMetadata filters (apply with AND):\n{block}"


def render_answer(record):
    """Expected answer prefixed with the CELEX id (the agent outputs the id).

    Tier-E (unanswerable) records carry no grounding doc, so the expected_answer
    - the stand-alone 'documents do not precisely answer' statement - is used
    verbatim with no CELEX prefix.
    """
    if record.get("unanswerable"):
        return record["expected_answer"]
    return f"CELEX {record['source_celex_id']} - {record['expected_answer']}"


def load_titles():
    titles = {}
    with CORPUS.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            titles[r["celex_id"]] = r["title"]
    return titles


def main():
    titles = load_titles()
    # validate every grounding doc exists in the corpus (tier-E records have none)
    missing = [r["source_celex_id"] for r in RECORDS
               if not r.get("unanswerable") and r["source_celex_id"] not in titles]
    if missing:
        raise SystemExit(f"Grounding docs not found in corpus: {missing}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1) rich source-of-truth file
    source_path = OUT_DIR / "multieurlex_eval_set_source.csv"
    fieldnames = [
        "id", "tier", "question", "filters", "expected_answer", "rubric",
        "source_celex_id", "source_title", "metadata_used",
        "distractor_celex_ids", "notes",
    ]
    with source_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in RECORDS:
            row = dict(r)
            row.pop("unanswerable", None)
            row["source_title"] = titles.get(r["source_celex_id"], "")
            # question column carries the full prompt sent to the agent
            # (prose + filter block); 'filters' lists the block separately
            row["question"] = render_question(r)
            row["filters"] = "; ".join(f"{lbl}={val}" for lbl, val in FILTERS.get(r["id"], []))
            row["expected_answer"] = render_answer(r)
            w.writerow(row)

    # all rendered questions must respect the 500-char limit shared by both templates
    for r in RECORDS:
        rq = render_question(r)
        if len(rq) > 500:
            raise SystemExit(f"{r['id']} question exceeds 500 chars ({len(rq)})")

    # 2a) Copilot Studio "Import conversations" file. Matches the layout of
    #     data/eval/EvalConversationTemplate.csv: a block of '#' comment lines,
    #     then conversationNumber, question, response. One conversation per
    #     question keeps the tricky cases context-independent.
    conv_path = OUT_DIR / "multieurlex_eval_set_copilot_import_conversation.csv"
    conv_comments = [
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
    with conv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        for line in conv_comments:
            w.writerow([line])
        w.writerow(["conversationNumber", "question", "response"])
        for i, r in enumerate(RECORDS, start=1):
            w.writerow([str(i), render_question(r), render_answer(r)])

    # 2b) Copilot Studio "classic" single-response file. Matches the layout of
    #     data/eval/EvaluationTemplate_classic.csv: '#' comment lines, then
    #     question, expectedResponse. Unlike the conversation template,
    #     expectedResponse IS used by the match / similarity / compare-meaning
    #     test methods, so the precise answer goes there.
    classic_path = OUT_DIR / "multieurlex_eval_set_copilot_import_classic.csv"
    classic_comments = [
        "# Import the test cases you want to use to test your agent",
        "#",
        "# Limitations",
        "# - maximum of 100 questions",
        "# - maximum 500 characters per question including spaces",
        "#",
        "# Imported columns",
        "# question - User question that the agent will answer.",
        "# expectedResponse - Expected responses to run match, similarity and "
        "compare meaning test cases.",
        "#",
        "# Test methods",
        "# - Test methods are not included in this template. You can configure "
        "test methods after importing the test cases.",
        "# - Initially, the default test method will be added to the imported "
        "test set.",
        "#",
        "# For more information, see the documentation.",
        "#",
    ]
    if len(RECORDS) > 100:
        raise SystemExit(f"Too many questions: {len(RECORDS)} (max 100)")
    with classic_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        for line in classic_comments:
            w.writerow([line])
        w.writerow(["question", "expectedResponse"])
        for r in RECORDS:
            w.writerow([render_question(r), render_answer(r)])

    print(f"Wrote {source_path} ({len(RECORDS)} rows)")
    print(f"Wrote {conv_path} ({len(RECORDS)} conversations)")
    print(f"Wrote {classic_path} ({len(RECORDS)} questions)")
    # tier summary
    from collections import Counter
    tiers = Counter(r["tier"] for r in RECORDS)
    print("Tier distribution:", dict(sorted(tiers.items())))


if __name__ == "__main__":
    main()
