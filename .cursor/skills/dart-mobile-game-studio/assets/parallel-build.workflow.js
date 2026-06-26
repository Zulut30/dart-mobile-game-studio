// parallel-build.workflow.js — tiered subagents across models, running in parallel.
//
// A reference Workflow script (run it with the Workflow tool: pass this file via scriptPath, or
// adapt it inline). It demonstrates the model-routing doctrine from references/model-routing.md:
// heavy roles on a top model, light roles on a cheap/fast one, and independent stages overlapping
// so the build uses the right brain for each job at the same wall-clock time.
//
//   Design (heavy)  ->  Build: gameplay [heavy]  ||  copy [light]  ||  art [light]  ->  Verify
//
// Pass a brief via the Workflow `args`, e.g. args: { brief: "a 12-card memory match for ages 4-8" }.
// Tier->model mirrors sync-agents.py CLAUDE_TIER_MODEL; change it in one place if the mapping moves.

export const meta = {
  name: 'parallel-build',
  description: 'Build a game with tiered subagents running in parallel across models',
  phases: [
    { title: 'Design', detail: 'Mini-GDD + architecture (heavy)' },
    { title: 'Build', detail: 'gameplay (heavy) + copy & art (light) in parallel' },
    { title: 'Verify', detail: 'tests (medium) then review (heavy)' },
  ],
}

// Tier -> Claude model (keep in sync with .agents/agents/sync-agents.py: CLAUDE_TIER_MODEL).
const MODEL = { heavy: 'opus', medium: 'sonnet', light: 'haiku' }
const brief = (args && args.brief) || 'a simple, kid-safe 2D mobile game'

phase('Design')
// game-designer (heavy) writes the Mini-GDD; engine-architect (heavy) turns it into an architecture.
const design = await agent(
  `Act as the game-designer. Produce a one-page Mini-GDD for: ${brief}. ` +
    `Return only the GDD markdown.`,
  { agentType: 'game-designer', model: MODEL.heavy, label: 'design:gdd' },
)
const arch = await agent(
  `Act as the engine-architect. Given this Mini-GDD:\n\n${design}\n\n` +
    `Choose the mode (Flutter-widgets / Flame / hybrid), define the pure-Dart core (models + systems, ` +
    `no package:flutter import), the state machine, and the folder layout. Return the architecture note.`,
  { agentType: 'engine-architect', model: MODEL.heavy, label: 'design:arch' },
)

phase('Build')
// Heavy implementation runs CONCURRENTLY with light content + art — three models, one wall-clock.
const [code, copy, art] = await parallel([
  () =>
    agent(
      `Act as the gameplay-programmer. Implement the MVP per this architecture:\n\n${arch}\n\n` +
        `Pure-Dart core + thin UI; clamp dt; inject a seeded Random; dispose everything; analyzer-clean. ` +
        `Return a summary of the files written and key decisions.`,
      { agentType: 'gameplay-programmer', model: MODEL.heavy, phase: 'Build', label: 'build:code' },
    ),
  () =>
    agent(
      `Act as the narrative-writer. From this Mini-GDD:\n\n${design}\n\n` +
        `Write menu / win / onboarding / empty-state copy — kids-safe, no dark patterns, ` +
        `localization-ready. Return the strings.`,
      { agentType: 'narrative-writer', model: MODEL.light, phase: 'Build', label: 'build:copy' },
    ),
  () =>
    agent(
      `Act as the art-director. From this Mini-GDD:\n\n${design}\n\n` +
        `Specify placeholder art-as-code (CustomPainter / vector shapes), a palette with WCAG-AA ` +
        `contrast and never-color-alone pairing, and an asset manifest. Return the art spec.`,
      { agentType: 'art-director', model: MODEL.light, phase: 'Build', label: 'build:art' },
    ),
])

phase('Verify')
// medium tests, then heavy review — both gated on the build result.
const tests = await agent(
  `Act as the qa-tester. For this implementation:\n\n${code}\n\n` +
    `Write dart test cases for the pure core: state transitions, scoring, win/lose, level parsing, ` +
    `and seeded-Random determinism. Return the test plan and the test files.`,
  { agentType: 'qa-tester', model: MODEL.medium, label: 'verify:tests' },
)
const review = await agent(
  `Act as the code-reviewer. Review the implementation and tests:\n\n${code}\n\n${tests}\n\n` +
    `Tag every finding with its references/common-pitfalls.md classifier code + severity. ` +
    `Return the review and a one-line verdict.`,
  { agentType: 'code-reviewer', model: MODEL.heavy, label: 'verify:review' },
)

return { design, arch, code, copy, art, tests, review }
