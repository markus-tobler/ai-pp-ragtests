# Evaluation Results — Static Analysis

_Generated 2026-06-29T14:10:56 from `data/eval/results`._

Runs analyzed: **2** · agents seen: **6** · eval methods: `CompareMeaning`, `GeneralQuality`.

**Pass/fail scoring uses the `CompareMeaning` method only**; other methods are reported per-method for reference but do not affect the headline pass rate, the passed/failed counts, or the failing-question analysis.

**Errors (timeouts).** Cases where the agent returned nothing to grade (empty response) are counted as errors, shown in the absolute counts, but excluded from the pass-rate denominator — pass rate = passed / (passed + failed), errors not in the divisor.

This report restates the numbers in the result files; it draws no conclusions. Note that agents do not all share the same case count, so pass rates compare proportions over different sample sizes.

## Across runs

![Agent pass rate across runs](charts/passrate_across_runs.png)

| Agent | gpt-5-chat | sonnet-4-6 |
|---|---|---|
| MultiEURLEX Classic DV Knowledge | 87.5% (35/40) | 100.0% (40/40) |
| MultiEURLEX Classic DV Table | 50.0% (20/40) | 91.9% (34/37) +3E |
| MultiEURLEX Classic Knowledge | 65.0% (26/40) | 97.4% (38/39) +1E |
| MultiEURLEX Classic MCP | 95.0% (38/40) | 100.0% (39/39) +1E |
| MultiEURLEX Classic MCP plus Semantic | 95.0% (38/40) | 100.0% (38/38) +2E |
| MultiEURLEX Classic Semantic | 80.0% (32/40) | 92.5% (37/40) |

## Run: gpt-5-chat

_generated `2026-06-29T12:10:52.826080+00:00` · source `data/eval/results/gpt-5-chat/summary.json`_

![Pass rate by agent](charts/passrate_by_agent__gpt-5-chat.png)

![Passed vs failed cases](charts/passfail_stacked__gpt-5-chat.png)

![Per-method pass rate](charts/method_passrate__gpt-5-chat.png)

| Agent | Cases | Passed (CompareMeaning) | Failed | Errors | Pass rate | CompareMeaning | GeneralQuality |
|---|---|---|---|---|---|---|---|
| MultiEURLEX Classic DV Knowledge | 40 | 35 | 5 | 0 | 87.5% | 87.5% (35/40) | 80.0% (32/40) |
| MultiEURLEX Classic DV Table | 40 | 20 | 20 | 0 | 50.0% | 50.0% (20/40) | 42.5% (17/40) |
| MultiEURLEX Classic Knowledge | 40 | 26 | 14 | 0 | 65.0% | 65.0% (26/40) | 62.5% (25/40) |
| MultiEURLEX Classic MCP | 40 | 38 | 2 | 0 | 95.0% | 95.0% (38/40) | 80.0% (32/40) |
| MultiEURLEX Classic MCP plus Semantic | 40 | 38 | 2 | 0 | 95.0% | 95.0% (38/40) | 82.5% (33/40) |
| MultiEURLEX Classic Semantic | 40 | 32 | 8 | 0 | 80.0% | 80.0% (32/40) | 65.0% (26/40) |

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

_generated `2026-06-29T12:10:52.842272+00:00` · source `data/eval/results/sonnet-4-6/summary.json`_

![Pass rate by agent](charts/passrate_by_agent__sonnet-4-6.png)

![Passed vs failed cases](charts/passfail_stacked__sonnet-4-6.png)

![Per-method pass rate](charts/method_passrate__sonnet-4-6.png)

| Agent | Cases | Passed (CompareMeaning) | Failed | Errors | Pass rate | CompareMeaning | GeneralQuality |
|---|---|---|---|---|---|---|---|
| MultiEURLEX Classic DV Knowledge | 40 | 40 | 0 | 0 | 100.0% | 100.0% (40/40) | 87.5% (35/40) |
| MultiEURLEX Classic DV Table | 40 | 34 | 3 | 3 | 91.9% | 91.9% (34/37) +3E | 73.0% (27/37) +3E |
| MultiEURLEX Classic Knowledge | 40 | 38 | 1 | 1 | 97.4% | 97.4% (38/39) +1E | 92.3% (36/39) +1E |
| MultiEURLEX Classic MCP | 40 | 39 | 0 | 1 | 100.0% | 100.0% (39/39) +1E | 89.7% (35/39) +1E |
| MultiEURLEX Classic MCP plus Semantic | 40 | 38 | 0 | 2 | 100.0% | 100.0% (38/38) +2E | 94.7% (36/38) +2E |
| MultiEURLEX Classic Semantic | 40 | 37 | 3 | 0 | 92.5% | 92.5% (37/40) | 85.0% (34/40) |

### Top 10 failing questions

![Top failing questions heatmap](charts/top_failures__sonnet-4-6.png)

Ranked by number of agents whose `CompareMeaning` check failed (then by errors). Errors (timeouts) are listed separately and are not counted as failures.

| # | Question | Asked by | Failed | Failing agents | Errored agents |
|---|---|---|---|---|---|
| 1 | Which act in the corpus sets out the data subject's right to erasure (the 'right to be fo… | 6 | 2/6 | DV Table, Knowledge | — |
| 2 | Among the Directives that add active substances to the biocidal products Directive 98/8/E… | 6 | 1/6 | Semantic | DV Table, MCP plus Semantic |
| 3 | Which 2014 EU Regulation lays down the rules on the information that Member States must s… | 6 | 1/6 | Semantic | — |
| 4 | Which 2015 Council Directive in the Finance domain adds a common minimum anti-abuse rule … | 6 | 1/6 | DV Table | — |
| 5 | Which 2014 Regulation in the Transport domain amends the EU Emissions Trading System Dire… | 6 | 1/6 | DV Table | — |
| 6 | Which 2014 Regulation amends Regulation (EC) No 539/2001 on the visa lists, and which thi… | 6 | 1/6 | Semantic | — |
| 7 | Which EU regulation lays down the model for operational programmes under the Investment f… | 6 | 0/6 | — | DV Table |
| 8 | Which EU act amends the rules protecting groundwater against pollution and deterioration … | 6 | 0/6 | — | MCP |
| 9 | Which 2013 Directive in the Trade domain amends the batteries Directive 2006/66/EC as reg… | 6 | 0/6 | — | Knowledge |
| 10 | Two 2014 Regulations adjust the remuneration and pensions of EU officials - one with effe… | 6 | 0/6 | — | DV Table |
