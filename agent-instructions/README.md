# Agent Instructions

Source of truth for Copilot Studio agent instructions. Agents are managed
**online** in Copilot Studio — these files are the canonical copy of each
agent's system prompt and conversation starters, version-controlled here and
pasted into the portal.

## Convention

- One file per agent: `<agent-slug>.md`. A single agent may have several
  instruction **variants** (e.g. different retrieval strategies) as
  `<agent-slug>-<variant>.md`, distinguished by the `variant:` frontmatter key.
  Variants share the same `agent`/`schemaName`/environment and are swapped into
  the same Copilot Studio agent for A/B evaluation.
- Each file has YAML frontmatter (identity/config) + an `## Instructions`
  section (the system prompt, verbatim, paste-ready) + a
  `## Conversation starters` section.
- Edit here first, commit, then paste `## Instructions` into the agent's
  instructions box in Copilot Studio and update the conversation starters.
- Keep the prompt plain-text paste-ready: ASCII punctuation, no code fences
  inside the Instructions section.

## Instruction files

All four files share one identical instruction body (identity, available fields,
relevance check, answer rules, conversation starters) and **differ only in the
`RETRIEVAL STRATEGY` section** — the variable under test.

| File | Variant (retrieval strategy) |
|---|---|
| [multieurlex-search-agent-mcp.md](multieurlex-search-agent-mcp.md) | mcp — `read_query`: metadata filters (AND) + keyword/synonym OR text match over title/text/domain, relax if empty |
| [multieurlex-search-agent-semantic.md](multieurlex-search-agent-semantic.md) | semantic — Semantic Search with a natural-language semantic query, broaden if empty |
| [multieurlex-search-agent-hybrid.md](multieurlex-search-agent-hybrid.md) | hybrid — always runs BOTH the mcp and semantic paths, then consolidates |
| [multieurlex-search-agent-knowledge.md](multieurlex-search-agent-knowledge.md) | knowledge — grounded on the agent's attached knowledge source (no tools) |

## Agents

Each agent is a permanent Copilot Studio agent with one instruction variant applied.
Edit the instruction file, commit, then paste into the agent's instructions box in the portal.

| Agent | Bot ID | Instruction file | Environment |
|---|---|---|---|
| MultiEURLEX Classic MCP | `3178427b-3b5b-48f5-ae8b-8815c8e009dd` | [multieurlex-search-agent-mcp.md](multieurlex-search-agent-mcp.md) | your-env |
| MultiEURLEX Classic Semantic | `7dc480d4-4c8a-433d-ad19-215599a24dc5` | [multieurlex-search-agent-semantic.md](multieurlex-search-agent-semantic.md) | your-env |
| MultiEURLEX Classic MCP plus Semantic | `8e544f18-eb71-f111-ab0d-000d3a340a6f` | [multieurlex-search-agent-hybrid.md](multieurlex-search-agent-hybrid.md) | your-env |
| MultiEURLEX Classic Knowledge | `1c6a788a-6a77-4586-b528-d8b3c1d272e8` | [multieurlex-search-agent-knowledge.md](multieurlex-search-agent-knowledge.md) | your-env |
| MultiEURLEX Classic DV Knowledge | `b6a6468d-632d-49df-93a1-aa1a9afbf4d6` | [multieurlex-search-agent-knowledge.md](multieurlex-search-agent-knowledge.md) | your-env |
