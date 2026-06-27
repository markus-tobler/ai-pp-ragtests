# Agent Instructions

Source of truth for Copilot Studio agent instructions. Agents are managed
**online** in Copilot Studio — these files are the canonical copy of each
agent's system prompt and conversation starters, version-controlled here and
pasted into the portal.

## Convention

- One file per agent: `<agent-slug>.md`.
- Each file has YAML frontmatter (identity/config) + an `## Instructions`
  section (the system prompt, verbatim, paste-ready) + a
  `## Conversation starters` section.
- Edit here first, commit, then paste `## Instructions` into the agent's
  instructions box in Copilot Studio and update the conversation starters.
- Keep the prompt plain-text paste-ready: ASCII punctuation, no code fences
  inside the Instructions section.

## Agents

| File | Agent | Environment |
|---|---|---|
| [multieurlex-search-agent.md](multieurlex-search-agent.md) | MultiEURLEX Search Agent | mto-training-management |
