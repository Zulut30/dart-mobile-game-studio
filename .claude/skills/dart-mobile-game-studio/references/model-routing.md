# Model routing — tiered subagents across models

Run heavy roles on a top model and light roles on a cheap/fast one, **in parallel**, so a build uses
the right brain for each job. The skill routes by a tool-agnostic **tier**, not a hard-coded model
name — so the same 14 agents map onto Claude Code, Cursor, or Codex without edits.

## The idea: tier, not a model name

Each agent declares a `tier` in its canonical frontmatter (`.agents/agents/<name>.md`):

```yaml
tier: heavy   # heavy | medium | light
```

Every tool resolves that tier to its own model line. Hard-coding `model: opus` in 14 files would break
on Cursor/Codex and rot when a model is renamed; a tier is portable and survives version churn — you
change one table, not 14 files.

## Tier → model (per tool)

| Tier | Claude Code (`model:`) | Cursor | Codex / GPT |
|---|---|---|---|
| **heavy** | Opus 4.8 (`opus`) | Opus-class | GPT-5.5 xHigh |
| **medium** | Sonnet 4.6 (`sonnet`) | Sonnet-class | GPT-5.4 |
| **light** | Haiku 4.5 (`haiku`) | Haiku-class | GPT-5.4-mini |

The Claude column is enforced mechanically — `sync-agents.py` writes `model: <opus|sonnet|haiku>` into
`.claude/agents/*.md` (see [How it's wired](#how-its-wired)). The Cursor column ships as a tier note in
each `.mdc`. The Codex/GPT column is the recommended cross-vendor mapping (see
[Cross-vendor](#cross-vendor-gpt)).

## Agent tiers (the 14 roles)

| Tier | Agents | Why this tier |
|---|---|---|
| **heavy** (8) | `game-coordinator`, `engine-architect`, `gameplay-programmer`, `code-auditor`, `security-auditor`, `performance-auditor`, `game-designer`, `code-reviewer` | Decomposition, architecture, the main code, whole-base audit, security, subtle perf, design, and diff review — reasoning-heavy work where a mistake is expensive |
| **medium** (3) | `qa-tester`, `legal-compliance`, `release-engineer` | Structured work in a narrow context: writing tests, walking a rules checklist, the release procedure |
| **light** (3) | `narrative-writer`, `art-director`, `balance-economist` | Template/spec-driven generation: copy, art-as-code from a spec, numeric tuning |

## How it's wired

1. **Declare** — `tier:` in the canonical agent frontmatter. Source of truth.
2. **Resolve** — `.agents/agents/sync-agents.py` maps `tier → model` (`CLAUDE_TIER_MODEL`) and writes
   `model: …` into the Claude copy (dropping `tier`), and a tier note into the Cursor copy.
   `validate-skill.sh` fails if any agent lacks a valid tier or an unresolved model — so drift can't ship.
3. **Execute** — `game-coordinator` returns a delegation plan that tags each step with its agent (and
   thus its tier/model). The main thread runs those steps — sequential where dependencies force it,
   **parallel where they don't** — each on its routed model.

## Running them in parallel

**A. Inline Agent calls (simplest).** After the coordinator's plan, launch independent steps in one
message so they run concurrently, each on its tier's model:

```
# heavy implementation + light content, at the same time:
Agent(subagent_type="gameplay-programmer", model="opus",  prompt="Implement the core + systems …")
Agent(subagent_type="narrative-writer",    model="haiku", prompt="Write menu/win/onboarding copy …")
Agent(subagent_type="art-director",        model="haiku", prompt="Author placeholder art-as-code …")
```

(Claude Code's `Agent` tool takes a `model`; a subagent's frontmatter `model:` is the default if you
omit it. Long jobs can use `run_in_background`.)

**B. Workflow orchestration (deterministic).** For a repeatable pipeline with real fan-out, use the
shipped template [`assets/parallel-build.workflow.js`](../assets/parallel-build.workflow.js): it runs
the design → parallel(build heavy + content light) → test (medium) → review (heavy) flow with
`agent({model, agentType})`, so each stage lands on its tier's model and independent stages overlap.

## Cross-vendor (GPT)

Claude Code runs only Claude models, so the `tier` abstraction is what makes GPT reachable:

- **In Codex** — the skill is portable; Codex resolves the same `tier` to its GPT line (the table
  above). No code change — the tier is already there.
- **Inside Claude Code** — to actually call GPT, add an MCP server that proxies to the OpenAI API and
  have a thin agent forward the prompt to it. This needs an API key and is an advanced add-on; the
  native path (Claude tiers) covers the parallel-multi-model goal without it.

## Why this is efficient

- **Portable** — one tier label works across Claude Code, Cursor, Codex; no per-tool duplication.
- **Cheaper** — the top model runs only the 8 heavy roles; medium/light go to faster, cheaper models.
- **Actually concurrent** — independent agents (inline or `Workflow.parallel`) overlap instead of
  running one-after-another.
- **Stable** — a model rename/upgrade is a one-line edit to `CLAUDE_TIER_MODEL` (and this table).

## Changing the mapping

- **Re-tier an agent:** edit `tier:` in `.agents/agents/<name>.md`, then run `sync-agents.py`.
- **Re-point a tier to a different model:** edit `CLAUDE_TIER_MODEL` in `sync-agents.py` (and this
  table), then re-sync. `validate-skill.sh` confirms every copy resolved.
