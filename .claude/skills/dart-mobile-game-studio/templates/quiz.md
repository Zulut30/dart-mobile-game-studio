# Template: Quiz (question → answer)

A **design brief + architecture skeleton** for a quiz / trivia game. Self-contained (no recipe in
`game-templates.md`). Implement with [`workflows/create-new-game.md`](../workflows/create-new-game.md)
+ [`add-level-system.md`](../workflows/add-level-system.md) (questions are level data).

**Mode:** Flutter-widgets-only. Discrete: show a question, take an answer, score, next. No loop.

---

## Mini-GDD (filled example — adapt)

- **One-liner:** `<answer multiple-choice questions; beat your score>`.
- **Audience & age:** ages 5+ (picture quiz) or general; sessions 1–3 min / 5–10 questions.
- **Core loop:** show question + options → tap an answer → immediate right/wrong feedback → next → final score.
- **Primary verb:** tap (choose).
- **Failure model:** **no hard fail** — wrong answers cost score/streak, not a Game Over; optional timer per question for older players.
- **Win / progression:** score, streak, category packs, star rating; "play again" reshuffles.
- **Art:** clean cards; picture-based options for pre-readers; clear correct/incorrect states (not color alone).
- **Scope (in):** one question bank, multiple-choice, scoring, feedback, final screen, restart.
- **Cut-line (later):** categories, timer, lives, difficulty tiers, true/false & input types.

## Architecture skeleton (pure Dart, no Flutter import)

```
lib/models/   question.dart     # immutable: id, prompt, List<Option>, correctIndex, mediaRef?
              quiz_state.dart    # questions (ordered), index, score, streak, answers; phase; ==/hashCode
lib/systems/  quiz_loader.dart  # parse question-bank JSON -> List<Question>; pure, validated
              quiz_logic.dart    # answer(state, optionIndex) -> new state (score/streak/advance); pure
              question_order.dart# seeded shuffle of questions & options from an injected Random
lib/widgets/  quiz_screen.dart   # renders current question + options; feedback; progress; result
```

- **Questions are JSON data**, parsed by a pure loader and validated (every question has a valid
  `correctIndex`, ≥2 options) — never code.
- **Deterministic order** — shuffle questions/options with an injected seeded `Random` so a run is
  reproducible in tests (and fair across replays).
- **Answer logic is pure** — `answer(state, i)` returns the new state (correct?, score, streak,
  next index, or finished); the view just renders and animates feedback.

## Genre specifics (what matters here)

- **Don't leak the answer** — option order shuffled; correct state shown by icon + text, not color alone.
- **Validate the bank on load** — a question with no/!valid `correctIndex` should fail loudly in tests, not mislead a player.
- **Pre-reader mode** — support image/audio prompts and options so under-6s can play; pair with TTS/`Semantics`.
- **Kids:** no timers/penalties for the youngest; no leaderboards/accounts; offline.

## Genre checklist

- [ ] Question bank is validated JSON; loader unit-tested (rejects malformed questions).
- [ ] Answer/scoring/advance logic is pure and unit-tested; finished-state correct.
- [ ] Question/option order from an injected seeded `Random`; same seed → same run.
- [ ] Correct/incorrect shown by shape+text (not color alone); `Semantics` on every option.
- [ ] No `package:flutter` in `models/`/`systems/`; no accounts/tracking; offline.

## See also
- [`workflows/create-new-game.md`](../workflows/create-new-game.md) · [`workflows/add-level-system.md`](../workflows/add-level-system.md) (question banks as data).
- [`references/asset-pipeline.md`](../references/asset-pipeline.md) (JSON schema) · [`references/accessibility-child-safety.md`](../references/accessibility-child-safety.md).
- [`templates/educational-kids.md`](educational-kids.md) — when the quiz is a learning tool for young children.
