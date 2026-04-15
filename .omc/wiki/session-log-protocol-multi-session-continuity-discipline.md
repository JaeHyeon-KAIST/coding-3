---
title: "Session-log protocol — multi-session continuity discipline"
tags: ["session-log", "protocol", "documentation", "multi-session", "continuity"]
created: 2026-04-15T00:19:20.716Z
updated: 2026-04-15T00:19:20.716Z
sources: []
links: []
category: convention
confidence: medium
schemaVersion: 1
---

# Session-log protocol — multi-session continuity discipline

# Session-log protocol

This is a long-running multi-session project (5+ sessions guaranteed). Without explicit session-log discipline, context drifts and re-discovery cost compounds. This page defines the protocol both human and AI must follow.

## When to write a session-log entry

**Mandatory:**
- End of any work session lasting > 30 minutes of focused activity
- After completing any milestone (M-series in `STRATEGY.md` §10)
- After a non-trivial decision (algorithm change, scope change, blocker resolution)
- Before starting a long-running background job (e.g., M6 evolution overnight)

**Recommended (but optional):**
- Mid-session if a notable observation surfaces (e.g., "this fixes the deadlock")
- After a session-search reveals duplicated work (record the pattern so it's caught next time)

## Where entries go

- Tool: `wiki_ingest` (MCP tool — already wired)
- Category: `session-log`
- Title format: `YYYY-MM-DD - <topic-slug>` (date-prefixed for chronological sort)
- Tags: include date (`YYYY-MM-DD`), milestone (`m1`, `m2a`, `m4`), and topic keywords

The `wiki_ingest` tool auto-generates the filename slug (`session-2026-04-15-m3-smoke-deadlock.md`) and adds the page to the auto-maintained wiki index.

## What each entry must contain

```markdown
# Session YYYY-MM-DD — <topic>

## Date / Session ID
2026-04-15, session 134a0e0e-...

## Focus (1 sentence)
What you set out to do this session.

## Activities (bullet list)
- Concrete actions taken (commands run, files edited, agents launched)
- Include cross-references: commit hashes, agent IDs, file paths
- Each bullet should be checkable against `git log` or filesystem

## Observations (only the non-obvious)
- Things you didn't expect or that go against the plan
- Empirical results vs predictions
- Anything a future session needs to know

## Decisions (with rationale)
- Choices made + WHY (so future-you doesn't re-litigate)
- Cross-link to wiki decision/ pages or STRATEGY.md ADR sections
- Format: "DECISION: ... | REASON: ... | ALTERNATIVES CONSIDERED: ..."

## Open items / blockers
- Cross-references to wiki debugging/ pages
- Anything that's NOT resolved this session
- Mark as OPEN until closed in a later session-log entry

## Next-session priority (one sentence per item, ordered)
1. Single most important thing to start when this resumes
2. Backup if #1 is blocked
3. (optional) Background task that can fire-and-forget

## Time spent (rough)
~45 minutes (helps calibrate future estimates)
```

## What entries are NOT for

- **Don't** restate STRATEGY.md or AI_USAGE.md content. Cross-reference instead.
- **Don't** dump full command output. Summarize + link to artifact.
- **Don't** write entries for trivial sessions (< 15 min, no decisions, no observations).

## How to USE entries (in future sessions)

At session start (every time), in this order:
1. `wiki_query --category session-log --query "<recent topic>"` or just `wiki_list --category session-log` and read the latest 1-2
2. Cross-reference to any OPEN debugging/ pages they link to
3. Read the "Next-session priority" of the last entry
4. **Don't** re-derive what the last session figured out — trust the entry

## Cross-references to other persistence

| For information about... | Read this first |
|---|---|
| Project rules, file edit whitelist | `CLAUDE.md` |
| Plan / ADR / milestones | `.omc/plans/STRATEGY.md` |
| Open questions (stretch / future) | `.omc/plans/open-questions.md` |
| Per-milestone code change log (channel-controlled) | `docs/AI_USAGE.md` |
| Current snapshot status | `.omc/STATUS.md` |
| New-session 5-min onboarding | `.omc/SESSION_RESUME.md` |
| Persistent memory (user-level, cross-project) | `~/.claude/projects/.../memory/MEMORY.md` |
| Working memory (7-day prune) | `.omc/notepad.md` Working section |
| Permanent project context | `.omc/project-memory.json` |
| Cross-session knowledge / hypotheses / patterns | This wiki (`.omc/wiki/`) |

## Auto Dream integration

Auto Dream consolidates `~/.claude/projects/.../memory/` after 24h + 5 sessions. session-log entries in this wiki are NOT touched by Auto Dream (they live in `.omc/wiki/`, not `~/.claude/projects/`). They are the manually-maintained complement to Auto Dream's automatic memory hygiene.

## Maintenance

- Run `wiki_lint` periodically (M6+) to catch stale entries, broken cross-references, oversized pages
- If a session-log entry's "Open items" all close, add a closing line: `**STATUS: All open items resolved as of YYYY-MM-DD (see session-log/...)**`
- Don't delete entries — historical record matters for the report Conclusion section

