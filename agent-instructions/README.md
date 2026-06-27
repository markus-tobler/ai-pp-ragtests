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

## Agents

All four files share one identical instruction body (identity, available fields,
relevance check, answer rules, conversation starters) and **differ only in the
`RETRIEVAL STRATEGY` section** — the variable under test.

| File | Agent | Variant (retrieval strategy) | Environment |
|---|---|---|---|
| [multieurlex-search-agent.md](multieurlex-search-agent.md) | MultiEURLEX Search Agent | mcp — `read_query`: metadata filters (AND) + keyword/synonym OR text match over title/text/domain, relax if empty | your-env |
| [multieurlex-search-agent-semantic.md](multieurlex-search-agent-semantic.md) | MultiEURLEX Search Agent | semantic — Semantic Search with a natural-language semantic query, broaden if empty | your-env |
| [multieurlex-search-agent-hybrid.md](multieurlex-search-agent-hybrid.md) | MultiEURLEX Search Agent | hybrid — always runs BOTH the mcp and semantic paths, then consolidates | your-env |
| [multieurlex-search-agent-knowledge.md](multieurlex-search-agent-knowledge.md) | MultiEURLEX Search Agent | knowledge — grounded on the agent's attached knowledge source (no tools) | your-env |
