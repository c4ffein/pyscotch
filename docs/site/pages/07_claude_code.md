# Claude Code Integration

PyScotch ships with [Claude Code](https://claude.ai/code) skills and hooks
to help developers who use Claude as their coding assistant. This page explains
what they are, how to use them, and how they work.

## What Are Skills?

A **skill** is a markdown file that gives Claude specialized knowledge about
a project. When you invoke a skill (via `/pyscotch-dev` or automatically),
Claude gets project-specific context: API patterns, common pitfalls, testing
conventions, and file locations.

PyScotch includes a skill at `.claude/skills/pyscotch-dev.md` that covers:

- Scotch API patterns (resource management, error codes, random state)
- The `c_fopen` FILE\* compatibility shim
- Testing conventions (never modify tests, use `random_reset()`)
- Build and environment setup
- Key file locations

### Using the Skill

If you're working on PyScotch with Claude Code, the skill is automatically
available. You can reference it by asking Claude about PyScotch-specific
patterns:

```
> How should I handle the coarse graph when SCOTCH_dgraphCoarsen returns 1?

Claude will know (from the skill) that the coarse graph is invalid and
must not be cleaned up — it should be marked with _exit_called = True.
```

## What Are Hooks?

A **hook** is a shell command that runs automatically in response to
Claude Code events. PyScotch includes a hook configuration at
`.claude/settings.json`.

Hooks can automate repetitive setup:

```json
{ "hooks": { "PreToolUse": [ {
  "matcher": "Bash",
  "hooks": [ {
    "type": "command",
    "command": "echo 'Reminder: use PYSCOTCH_INT_SIZE=64 PYSCOTCH_PARALLEL=0 for sequential tests'" } ] } ] } }
```

This reminds Claude to set the right environment variables before running
shell commands — a common source of confusion when switching between
32-bit and 64-bit Scotch variants.

## Creating Your Own Skills

You can extend the PyScotch skill or create new ones. A skill is just
a markdown file in `.claude/skills/`:

```markdown
---
name: my-custom-skill
description: One-line description of what this skill provides
---

# My Custom Skill

Markdown content with project knowledge, patterns, examples...
```

The `description` field helps Claude decide when the skill is relevant.
The body can include code examples, tables, warnings — anything that
helps Claude work effectively on your project.

## The CLAUDE.md File

The project's `CLAUDE.md` at the repository root is always loaded by
Claude Code. It contains the canonical project instructions:

- Dependency management (`uv`, not `pip`)
- Submodule setup
- Testing philosophy (tests are never the problem — fix the implementation)
- Scotch API knowledge (error codes, sizing, init/exit patterns)

The skill in `.claude/skills/pyscotch-dev.md` extends this with more
structured, queryable knowledge. Think of `CLAUDE.md` as the rules
and the skill as the reference manual.

## Summary

| File | Purpose | When it's used |
|------|---------|----------------|
| `CLAUDE.md` | Project rules and constraints | Every conversation |
| `.claude/skills/pyscotch-dev.md` | API patterns and dev guide | When relevant to the task |
| `.claude/settings.json` | Hook configuration | Before tool execution |

These integrations mean that anyone cloning PyScotch and using Claude Code
gets project-aware assistance out of the box — no manual setup needed.
