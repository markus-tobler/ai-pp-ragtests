# Evaluation Results — Static Analysis

_Generated 2026-06-30T08:47:36 from `data/eval/results`._

Runs analyzed: **3** · agents seen: **6** · eval methods: `CompareMeaning`, `GeneralQuality`.

**Pass/fail scoring uses the `CompareMeaning` method only**; other methods are reported per-method for reference but do not affect the headline pass rate, the passed/failed counts, or the failing-question analysis.

**Errors (timeouts).** Cases where the agent returned nothing to grade (empty response) are counted as errors, shown in the absolute counts, but excluded from the pass-rate denominator — pass rate = passed / (passed + failed), errors not in the divisor.

This report restates the numbers in the result files; it draws no conclusions. Note that agents do not all share the same case count, so pass rates compare proportions over different sample sizes.

## Across runs

![Agent pass rate across runs](charts/passrate_across_runs.png)

| Agent | gpt-4-1 | gpt-5-chat | sonnet-4-6 |
|---|---|---|---|
| MultiEURLEX Classic DV Knowledge | 96.0% (48/50) | 90.0% (45/50) | 100.0% (50/50) |
| MultiEURLEX Classic DV Table | 60.0% (30/50) | 58.0% (29/50) | 93.6% (44/47) +3E |
| MultiEURLEX Classic Knowledge | 84.0% (42/50) | 68.0% (34/50) | 97.9% (46/47) +3E |
| MultiEURLEX Classic MCP | 76.0% (38/50) | 96.0% (48/50) | 100.0% (47/47) +3E |
| MultiEURLEX Classic MCP plus Semantic | 74.0% (37/50) | 92.0% (46/50) | 97.9% (46/47) +3E |
| MultiEURLEX Classic Semantic | 74.0% (37/50) | 76.0% (38/50) | 90.0% (45/50) |

## Run: gpt-4-1

_generated `2026-06-30T06:47:30.428704+00:00` · source `data/eval/results/gpt-4-1/summary.json`_

![Pass rate by agent](charts/passrate_by_agent__gpt-4-1.png)

![Passed vs failed cases](charts/passfail_stacked__gpt-4-1.png)

![Per-method pass rate](charts/method_passrate__gpt-4-1.png)

| Agent | Cases | Passed (CompareMeaning) | Failed | Errors | Pass rate | CompareMeaning | GeneralQuality |
|---|---|---|---|---|---|---|---|
| MultiEURLEX Classic DV Knowledge | 50 | 48 | 2 | 0 | 96.0% | 96.0% (48/50) | 94.0% (47/50) |
| MultiEURLEX Classic DV Table | 50 | 30 | 20 | 0 | 60.0% | 60.0% (30/50) | 54.0% (27/50) |
| MultiEURLEX Classic Knowledge | 50 | 42 | 8 | 0 | 84.0% | 84.0% (42/50) | 80.0% (40/50) |
| MultiEURLEX Classic MCP | 50 | 38 | 12 | 0 | 76.0% | 76.0% (38/50) | 78.0% (39/50) |
| MultiEURLEX Classic MCP plus Semantic | 50 | 37 | 13 | 0 | 74.0% | 74.0% (37/50) | 74.0% (37/50) |
| MultiEURLEX Classic Semantic | 50 | 37 | 13 | 0 | 74.0% | 74.0% (37/50) | 72.0% (36/50) |

### Top 10 failing questions

![Top failing questions heatmap](charts/top_failures__gpt-4-1.png)

Ranked by number of agents whose `CompareMeaning` check failed (then by errors). Errors (timeouts) are listed separately and are not counted as failures.

| # | Question | Asked by | Failed | Failing agents | Errored agents |
|---|---|---|---|---|---|
| 1 | Which act in the corpus sets out the data subject's right to erasure (the 'right to be fo… | 6 | 6/6 | DV Knowledge, DV Table, Knowledge, MCP, MCP plus Semantic, Semantic | — |
| 2 | Which 2015 EU directive sets a maximum permitted level for a foam-forming chemical in the… | 6 | 4/6 | Knowledge, MCP, MCP plus Semantic, Semantic | — |
| 3 | Which EU act includes pyriproxyfen as an active substance for biocidal products, and whic… | 6 | 3/6 | Knowledge, MCP plus Semantic, Semantic | — |
| 4 | Which 2013 Commission Directive in the Law domain amends Annex III to the rail interopera… | 6 | 3/6 | DV Table, MCP plus Semantic, Semantic | — |
| 5 | In the 2015 European Central Bank Decision on targeted longer-term refinancing operations… | 6 | 3/6 | DV Table, MCP, MCP plus Semantic | — |
| 6 | Which 2015 EU directive updates the rules on the dockside facilities that take in rubbish… | 6 | 3/6 | MCP, MCP plus Semantic, Semantic | — |
| 7 | Which EU regulation amended the rules on the single payment scheme and support to vine-gr… | 6 | 2/6 | Knowledge, MCP plus Semantic | — |
| 8 | Which EU regulation authorised the use of methacrylate copolymers as food additives in so… | 6 | 2/6 | DV Table, MCP plus Semantic | — |
| 9 | Which 2014 EU Regulation lays down the rules on the information that Member States must s… | 6 | 2/6 | MCP, MCP plus Semantic | — |
| 10 | Which 2014 EU Regulation amends Regulation (EU) No 965/2012 on the technical requirements… | 6 | 2/6 | DV Table, MCP | — |

## Run: gpt-5-chat

_generated `2026-06-30T06:47:30.446638+00:00` · source `data/eval/results/gpt-5-chat/summary.json`_

![Pass rate by agent](charts/passrate_by_agent__gpt-5-chat.png)

![Passed vs failed cases](charts/passfail_stacked__gpt-5-chat.png)

![Per-method pass rate](charts/method_passrate__gpt-5-chat.png)

| Agent | Cases | Passed (CompareMeaning) | Failed | Errors | Pass rate | CompareMeaning | GeneralQuality |
|---|---|---|---|---|---|---|---|
| MultiEURLEX Classic DV Knowledge | 50 | 45 | 5 | 0 | 90.0% | 90.0% (45/50) | 84.0% (42/50) |
| MultiEURLEX Classic DV Table | 50 | 29 | 21 | 0 | 58.0% | 58.0% (29/50) | 52.0% (26/50) |
| MultiEURLEX Classic Knowledge | 50 | 34 | 16 | 0 | 68.0% | 68.0% (34/50) | 64.0% (32/50) |
| MultiEURLEX Classic MCP | 50 | 48 | 2 | 0 | 96.0% | 96.0% (48/50) | 84.0% (42/50) |
| MultiEURLEX Classic MCP plus Semantic | 50 | 46 | 4 | 0 | 92.0% | 92.0% (46/50) | 80.0% (40/50) |
| MultiEURLEX Classic Semantic | 50 | 38 | 12 | 0 | 76.0% | 76.0% (38/50) | 66.0% (33/50) |

### Top 10 failing questions

![Top failing questions heatmap](charts/top_failures__gpt-5-chat.png)

Ranked by number of agents whose `CompareMeaning` check failed (then by errors). Errors (timeouts) are listed separately and are not counted as failures.

| # | Question | Asked by | Failed | Failing agents | Errored agents |
|---|---|---|---|---|---|
| 1 | Which EU act includes pyriproxyfen as an active substance for biocidal products, and whic… | 6 | 3/6 | DV Table, MCP plus Semantic, Semantic | — |
| 2 | Which 2013 Council Regulation in the employment and working conditions domain lays down t… | 6 | 3/6 | DV Knowledge, DV Table, Knowledge | — |
| 3 | Which 2015 Council Directive in the Finance domain adds a common minimum anti-abuse rule … | 6 | 3/6 | DV Knowledge, DV Table, Knowledge | — |
| 4 | Which 2015 CFSP Decision appoints the European Union Special Representative for Central A… | 6 | 3/6 | DV Table, Knowledge, Semantic | — |
| 5 | Which act in the corpus sets out the data subject's right to erasure (the 'right to be fo… | 6 | 3/6 | DV Knowledge, DV Table, Knowledge | — |
| 6 | Which EU act sets maximum residue levels for pesticides such as acetamiprid and tebuconaz… | 6 | 2/6 | DV Table, MCP plus Semantic | — |
| 7 | What does the 2015 EU Decision concerning restrictive measures in view of the situation i… | 6 | 2/6 | DV Table, Semantic | — |
| 8 | Which 2014 EU Regulation amends Regulation (EU) No 965/2012 on the technical requirements… | 6 | 2/6 | DV Table, MCP | — |
| 9 | Which 2014 Commission Implementing Regulation in the Finance domain governs the reimburse… | 6 | 2/6 | DV Table, Knowledge | — |
| 10 | A 2014 Commission Regulation in the Energy domain defines the criteria and geographic ran… | 6 | 2/6 | DV Knowledge, Knowledge | — |

## Run: sonnet-4-6

_generated `2026-06-30T06:47:30.473815+00:00` · source `data/eval/results/sonnet-4-6/summary.json`_

![Pass rate by agent](charts/passrate_by_agent__sonnet-4-6.png)

![Passed vs failed cases](charts/passfail_stacked__sonnet-4-6.png)

![Per-method pass rate](charts/method_passrate__sonnet-4-6.png)

| Agent | Cases | Passed (CompareMeaning) | Failed | Errors | Pass rate | CompareMeaning | GeneralQuality |
|---|---|---|---|---|---|---|---|
| MultiEURLEX Classic DV Knowledge | 50 | 50 | 0 | 0 | 100.0% | 100.0% (50/50) | 90.0% (45/50) |
| MultiEURLEX Classic DV Table | 50 | 44 | 3 | 3 | 93.6% | 93.6% (44/47) +3E | 76.6% (36/47) +3E |
| MultiEURLEX Classic Knowledge | 50 | 46 | 1 | 3 | 97.9% | 97.9% (46/47) +3E | 93.6% (44/47) +3E |
| MultiEURLEX Classic MCP | 50 | 47 | 0 | 3 | 100.0% | 100.0% (47/47) +3E | 91.5% (43/47) +3E |
| MultiEURLEX Classic MCP plus Semantic | 50 | 46 | 1 | 3 | 97.9% | 97.9% (46/47) +3E | 93.6% (44/47) +3E |
| MultiEURLEX Classic Semantic | 50 | 45 | 5 | 0 | 90.0% | 90.0% (45/50) | 84.0% (42/50) |

### Top 10 failing questions

![Top failing questions heatmap](charts/top_failures__sonnet-4-6.png)

Ranked by number of agents whose `CompareMeaning` check failed (then by errors). Errors (timeouts) are listed separately and are not counted as failures.

| # | Question | Asked by | Failed | Failing agents | Errored agents |
|---|---|---|---|---|---|
| 1 | Which act in the corpus sets out the data subject's right to erasure (the 'right to be fo… | 6 | 2/6 | DV Table, Knowledge | — |
| 2 | Among the Directives that add active substances to the biocidal products Directive 98/8/E… | 6 | 1/6 | Semantic | DV Table, MCP plus Semantic |
| 3 | Which 2015 EU directive sets a maximum permitted level for a foam-forming chemical in the… | 6 | 1/6 | Semantic | Knowledge |
| 4 | Which 2014 EU Regulation lays down the rules on the information that Member States must s… | 6 | 1/6 | Semantic | — |
| 5 | Which 2015 Council Directive in the Finance domain adds a common minimum anti-abuse rule … | 6 | 1/6 | DV Table | — |
| 6 | Which 2014 Regulation in the Transport domain amends the EU Emissions Trading System Dire… | 6 | 1/6 | DV Table | — |
| 7 | Which 2014 Regulation amends Regulation (EC) No 539/2001 on the visa lists, and which thi… | 6 | 1/6 | Semantic | — |
| 8 | Which EU directive aims to cut down how many flimsy throwaway shopping sacks each person … | 6 | 1/6 | MCP plus Semantic | — |
| 9 | Which EU directive revises the safeguards that keep underground water sources from becomi… | 6 | 1/6 | Semantic | — |
| 10 | Which EU act sets the permitted upper limits for traces of crop-treatment chemicals left … | 6 | 0/6 | — | MCP, MCP plus Semantic |
