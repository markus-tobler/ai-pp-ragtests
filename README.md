# AI PP RAG Tests

Evaluation project comparing knowledge-retrieval methods for Copilot Studio agents on the MultiEURLEX legal-document corpus.

## Start Here

- **Published report:** https://markus-tobler.github.io/ai-pp-ragtests/
- **Source report:** [reports/evaluation_report.md](reports/evaluation_report.md)

## What This Project Is About

This repository evaluates how different retrieval setups affect the quality of answers from Copilot Studio agents. The test corpus is a curated set of 300 English-language EU legal documents from MultiEURLEX. Each document has structured metadata such as CELEX id, document type, year, policy domain, and legal actor type.

The goal is practical: if an agent needs to answer questions over a legal or policy corpus, which knowledge setup works best? The project compares six retrieval configurations across the same 50-question evaluation set, using the same corpus and expected answers.

## Retrieval Methods Compared

The evaluation compares these approaches:

- **MCP:** structured Dataverse MCP queries using metadata filters and keyword matching.
- **Semantic:** a Dataverse semantic-search tool called with a natural-language query.
- **MCP plus Semantic:** both retrieval paths combined, then re-ranked.
- **Knowledge:** the whole corpus uploaded as one CSV knowledge file.
- **DV Knowledge:** one uploaded knowledge file per document.
- **DV Table:** a Dataverse table connected directly as a native knowledge source.

## How It Was Scored

The headline metric is **CompareMeaning** pass rate. A response passes when it means the same thing as the expected answer. Empty responses and timeouts are tracked as errors and excluded from the pass-rate denominator, so the report shows both accuracy and reliability.

The questions cover broad topical lookup, metadata-constrained lookup, precise legal disambiguation, distractor cases, unanswerable control questions, and semantic paraphrases.

## Main Takeaways

The best retrieval method depends on the model. GPT-4.1 performed best with per-document uploaded knowledge, GPT-5 Chat performed best with MCP, and Claude Sonnet 4.6 made several methods perform near perfectly on scored cases.

Across the full evaluation, structured MCP retrieval is the strongest default for metadata-rich Dataverse-backed corpora. For knowledge grounding, uploading one file per document is much stronger than using one large corpus file or native Dataverse table knowledge. Native Dataverse table knowledge was the weakest method on both GPT runs.

The stronger model reduced the gap between retrieval methods, but it also introduced timeout or empty-response cases for several configurations. That is why the report separates scored accuracy from operational errors.

## Repository Map

- [reports/evaluation_report.md](reports/evaluation_report.md) is the readable evaluation report.
- `data/eval/` contains the evaluation source files, import templates, generated results, and charts.
- `agent-instructions/` contains the instruction variants used for the tested agent configurations.
- `scripts/` contains utilities for building the evaluation set, collecting results, and analyzing outputs.

For the full write-up, charts, tables, and recommendations, start with the published report linked above.
