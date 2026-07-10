# dart-mobile-game-studio

[![CI](https://github.com/Zulut30/dart-mobile-game-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/Zulut30/dart-mobile-game-studio/actions/workflows/ci.yml)

Переносимый **Agent Skill** (навык для ИИ-агента), который позволяет ИИ-агенту для кодинга
(Claude Code, Cursor, Codex) собирать простые, отполированные 2D-игры для **iOS, iPadOS и Android**
на Flutter/Dart — и писать при этом **отличный Dart-код**.

Один кодовый базис на Flutter → три платформы. Упор на приватность и безопасность детей по умолчанию
(требования **Apple Kids Category** *и* **Google Play Families** одновременно).

> **Что такое «навык».** Это не приложение и не библиотека, которую вы импортируете. Это пакет
> инструкций, справочников, шаблонов и скриптов, который читает ИИ-агент, чтобы провести вас через
> полный цикл: идея → аудит → архитектура → прототип → продакшен-код → тесты → оптимизация →
> монетизация → релиз. Точка входа для агента — [`SKILL.md`](.agents/skills/dart-mobile-game-studio/SKILL.md).

---

## Какие игры покрывает

Простые 2D-жанры, которые реально довести до стора в одиночку или малой командой:

- 🎨 раскраски (tap-to-fill по векторным областям);
- 🧩 пазлы: «собери картинку» / «пятнашки» (jigsaw / sliding);
- 🏃 лёгкие платформеры (бег/прыжки, простая физика);
- ✋ drag-and-drop головоломки (перетаскивание в слоты, snap-to-grid);
- 🃏 «память» / поиск пар (memory / matching, без проигрыша);
- 🔷 сопоставление форм и цветов (shape matching);
- ♾️ лёгкие «бесконечные раннеры» (auto-run, тап-прыжок);
- ⚡ игры на реакцию (tap-reaction);
- 🎓 обучающие мини-игры для детей.

---

## Структура репозитория

```
.
├─ .agents/skills/dart-mobile-game-studio/   ← КАНОНИЧЕСКИЙ навык (правьте здесь)
│  ├─ SKILL.md                               ← точка входа: 9-шаговый workflow + правила
│  ├─ references/   (21 файл)                ← пайплайн, архитектура, Flame, a11y, тесты, перф,
│  │  │                                         каталог ошибок, безопасная автоматизация…
│  │  └─ dart/      (7 файлов)               ← «мастерство Dart» (как писать отличный Dart)
│  ├─ workflows/    (21 файл)                ← пошаговые playbook'и (создать игру, локализация, релиз…)
│  ├─ templates/    (9 + README)            ← жанровые дизайн-брифы + скелеты (casual…ui-heavy)
│  ├─ checklists/   (12 файлов)              ← tick-листы для ревьюера/агента по каждой области
│  ├─ assets/       (11 файлов)              ← парные pure-Dart + Flame/Widget-шаблоны, GDD,
│  │                                            JSON-схема, seeded RNG, analysis_options, чек-листы
│  └─ scripts/      (18 файлов)              ← sync, AI context/router/eval, self-review, validation,
│                                               fixture/scaffold, doctors, preflight, safe-run, logs, pub-cache
├─ .agents/agents/  (14 ролей + README)      ← КАНОНИЧЕСКИЕ субагенты + sync-agents.py
├─ .claude/skills/…  .claude/agents/         ← зеркала для Claude Code   (синхронизируются)
├─ .cursor/skills/…  .cursor/rules/agents/   ← зеркала для Cursor        (синхронизируются)
├─ .codex/agents/                            ← 14 TOML-профилей Codex    (синхронизируются)
├─ .cursor/rules/                            ← Cursor .mdc-правила (общее / архитектура / тесты)
├─ docs/ai-game-dev/upstream-build-spec.md   ← полная исходная спецификация (21 раздел)
├─ examples/memory_match/                    ← референс-игра (widgets): pure-Dart ядро + тесты + Flutter-UI
├─ examples/endless_runner/                  ← референс-игра (Flame): pure-ядро + FlameGame + тесты
├─ evals/task-routing.jsonl                  ← versioned RU/EN routing corpus
├─ .github/workflows/                        ← CI + Android/iOS release canary
├─ AGENTS.md                                 ← точка входа для Codex / AGENTS.md-инструментов
└─ CLAUDE.md                                 ← точка входа для Claude Code
```

**Источник истины — только `.agents/`.** Каталоги `.claude/` и `.cursor/` — это
сгенерированные зеркала; не правьте их руками (см. [Разработка навыка](#разработка-навыка)).

---

## Как агент использует навык

Агент читает `SKILL.md` и идёт по 9-шаговому workflow без пропусков:

1. **Понять запрос** — жанр, возраст, основной глагол (tap / drag / match / move), есть ли проигрыш,
   длина сессии, платформы, ориентация.
2. **Mini-GDD** — одностраничный дизайн-документ по [`assets/gdd-template.md`](.agents/skills/dart-mobile-game-studio/assets/gdd-template.md).
3. **Выбрать режим реализации** (см. ниже).
4. **Спроектировать архитектуру** — отделить **чистую Dart-логику** (модель + правила + конечный
   автомат, *без импортов Flutter*) от рендеринга. Ядро тестируется `dart test` без устройства.
5. **Реализовать MVP** — маленькие файлы, модульные папки `lib/models/ lib/systems/ lib/game/ lib/widgets/`.
6. **Написать тесты** — на чистую модель: легальные ходы, счёт, win/lose, загрузка уровней, переходы,
   детерминированные (seeded) перемешивания/спавны.
7. **Прогнать build/test** — `scripts/verify-flutter-project.sh` → `dart analyze` + `dart test` (+ `flutter test`).
   Если тулчейна нет — честно сказать об этом и дать точные команды.
8. **Ревью** — `assets/review-checklist.md`: безопасность детей, приватность, доступность, перф.
9. **Handoff** — что построено, выбранный режим и почему, **изменённые файлы**, **запущенные команды
   с реальным выводом**, допущения, риски, следующие шаги.

### Три режима реализации

| Режим | Когда | Технологии |
|---|---|---|
| **Flutter-widgets-only** | статичные/пошаговые доски: раскраски, «память», matching, drag-and-drop, реакция | `CustomPainter`/`Canvas`, `AnimatedBuilder`, жесты. Проще всего, максимально тестируемо |
| **Flame** | непрерывное движение, физика, спрайты, частицы: платформер, раннер | `FlameGame` + компоненты + игровой цикл (`update`/`render`); Forge2D для реальной физики |
| **Hybrid** | экшен, которому нужны и геймплей, и настоящие меню/HUD | геймплей на Flame внутри дерева Flutter через `GameWidget` + overlays |

---

## 14 специалистов-субагентов

Для крупных задач навык разворачивает «команду» из 14 ролей (канонические — в `.agents/agents/`,
зеркалируются в `.claude/agents/`, `.cursor/rules/agents/` и `.codex/agents/`). Субагенты не могут вызывать друг друга,
поэтому `game-coordinator` возвращает план делегирования, который главный поток выполняет по шагам.

- **Сборка:** `game-coordinator` (PM/декомпозиция) → `game-designer` → `engine-architect` →
  `gameplay-programmer` (+ параллельно `art-director`, `narrative-writer`, `balance-economist`) → `qa-tester`.
- **Ревью и аудит (read-only):** `code-reviewer` (по диффу/PR), а перед релизом — «гейт»:
  `code-auditor` (вся кодовая база), `security-auditor`, `performance-auditor`, `legal-compliance`.
- **Релиз:** `release-engineer` — готовность к подаче в **App Store** *и* **Google Play**.

**Мульти-модельная маршрутизация.** У каждого агента есть `tier` (heavy/medium/light), который
маршрутизирует его на модель: на Claude Code `sync-agents.py` резолвит tier→`model: opus|sonnet|haiku`
(heavy=Opus 4.8, medium=Sonnet 4.6, light=Haiku 4.5); в Codex — на линейку GPT (5.5 xHigh / 5.4 /
5.4-mini). Тяжёлые и лёгкие роли запускаются **параллельно** на своих моделях. Раскладка: 8 heavy /
3 medium / 3 light. Политика и шаблон оркестрации —
[`references/model-routing.md`](.agents/skills/dart-mobile-game-studio/references/model-routing.md) +
[`assets/parallel-build.workflow.js`](.agents/skills/dart-mobile-game-studio/assets/parallel-build.workflow.js).

Регенерация копий: `.agents/agents/sync-agents.py`. Подробности — в
[`.agents/agents/README.md`](.agents/agents/README.md).

---

## Ключевые доктрины (то, что навык заставляет соблюдать)

- **Чистое Dart-ядро.** Все правила игры — в `lib/models/` + `lib/systems/` **без `package:flutter`**.
  Тестируется `dart test` на VM, без устройства и без эмулятора.
- **Конечный автомат:** `menu → playing → paused → won/lost → menu` (sealed-классы / enum'ы).
- **Детерминизм через seeded RNG.** Везде внедряется `SeededRandom` (SplitMix64, bias-free `nextInt`
  через rejection sampling) — никаких `Random()` в игровой логике, чтобы тесты были воспроизводимыми.
- **Кадронезависимость.** `dt` всегда клампится вручную — **Flame не ограничивает `dt` за вас**.
- **Безопасность детей (обе платформы).** Без трекинга, аналитики, рекламы, AdvertisingId (IDFA/GAID),
  внешних ссылок, аккаунтов и тёмных паттернов; offline-first; никаких персональных данных; минимум
  разрешений (нет Android `INTERNET`, если игра офлайн); родительский гейт на чувствительные действия.
- **Только легальные ассеты.** Плейсхолдерная векторная графика (`CustomPainter`/`flutter_svg`) или
  ассеты, принадлежащие пользователю. Уровни — как JSON-данные, не как код.
- **Минимум зависимостей.** Порядок выбора: Flutter SDK → официальные пакеты flutter/dart → Flame →
  зрелые community-пакеты → DIY. Каждую зависимость нужно обосновать.
- **Никаких гарантий прохождения модерации.** На выходе — чек-лист и список рисков, не «одобрено стором».

---

## Карта справочников

### `references/` — глубокие разборы
`game-development-pipeline` · `flutter-game-architecture` · `flutter-flame-patterns` ·
`game-templates` · `asset-pipeline` · `accessibility-child-safety` · `testing-and-release` ·
`performance-checklist` · `flutter-games-toolkit` · `algorithms-for-games` (pathfinding BFS/Dijkstra/A*,
match-3, генерация лабиринтов, разрешимость пятнашек) · `ui-and-animations` · `production-quality` ·
`codegen-and-boilerplate` · `testing-e2e-patrol` · **`common-pitfalls`** (каталог ошибок:
приоритеты P0–P3, классификатор кодов, severity, матрица симптом→причина→фикс) · **`ci-and-automation`**
(политика безопасной автоматизации: preflight, savepoint/rollback, triage, кэш `pub get`) ·
**`model-routing`** (tier-маршрутизация 14 агентов по моделям + параллельная оркестрация).

### `references/dart/` — мастерство Dart
`README` (планка качества — начните отсюда) · `dart-language-essentials` · `dart-async-isolates` ·
`dart-api-design` · `flutter-widgets-mastery` · `dart-memory-performance` · `dart-patterns-idioms`.

### Политики (правила, которые применяют агенты) — `references/`
`package-policy` (порядок выбора зависимостей) · `quality-policy` (планка продакшен-качества) ·
`monetization-policy` (реклама/IAP/подписки с гейтом «дети vs 13+») · `release-policy` (правила подачи
в оба стора и ловушки отклонения).

### `checklists/` — tick-листы для ревью
`dart-code-quality` · `flutter-ui-quality` · `game-architecture` · `flame-quality` · `performance` ·
`accessibility` · `localization` · `asset-licensing` · `monetization` · `app-store-release` ·
`google-play-release` · `testing`.

### `workflows/` — пошаговые playbook'и (21)
*Сборка:* `create-new-game` · `choose-game-architecture` · `setup-flutter-project` ·
`setup-flame-project` · `add-game-loop` · `add-level-system` · `add-animations` ·
`add-assets-pipeline` · `add-audio` · `add-localization` · `add-state-management` · `add-navigation` ·
`add-save-system` · `write-tests`.
*Отладка и перф:* `debug-common-errors` (triage → классификатор → фикс) · `run-performance-audit`.
*Релиз:* `prepare-ios-release` · `prepare-android-release`.
*Монетизация (с гейтом «дети vs 13+»):* `add-monetization` · `add-ads` · `add-in-app-purchases`.

### `templates/` — жанровые дизайн-старты (9)
Заполняемый Mini-GDD + архитектурный скелет на жанр (дополняют рецепты `game-templates`):
`casual` · `coloring` · `card` · `puzzle` · `platformer-flame` · `endless-runner` · `quiz` ·
`educational-kids` · `ui-heavy`.

---

## Шаблоны и скрипты

**`assets/` (копировать и адаптировать):** `gdd-template.md`, `level-schema-template.json`
(JSON-схема Draft-07 для данных уровня), парные `flame_game_model_template.dart` +
`flame_game_template.dart` и `tile_game_model_template.dart` + `flutter_game_widget_template.dart`,
`seeded_random.dart`, `analysis_options.yaml` (строгие линты), `review-checklist.md`, `privacy-checklist.md`.

**`scripts/`:**

| Скрипт | Назначение |
|---|---|
| `sync-skill.sh` | зеркалирует канонический навык в `.claude/` и `.cursor/` (`--check` для CI) |
| `ai-context-pack.py` | AI context pack для агента: проекты, режимы, команды, правила, references, agents, findings (`--markdown`, `--json`, `--project`) |
| `task-router.py` | токенизирует задачу, сохраняет составные intents и маршрутизирует их в workflows/references/templates/agents/required checks (`--markdown`, `--json`, `--project`) |
| `router-eval.py` | измеряет router на RU/EN corpus: ≥95% accuracy, 100% critical и полное workflow/agent coverage |
| `self-review-loop.py` | замыкает цикл проверки ИИ после правки; repo-wide аудит автоматически проверяет все найденные проекты вместо ложного успеха без target |
| `discover-projects.sh` | единый поиск Dart/Flutter `pubspec.yaml` для single-project и multi-example repo (`--all`, `--dirs`, `--json`) |
| `doc-doctor.py` | проверяет Markdown links и backticked skill paths, которые обычный link checker не видит (`--json`) |
| `validate-skill.sh` | структурный gate + dependency-free black-box тесты критических CLI-контрактов |
| `verify-flutter-project.sh` | source-preserving format/analyze/test без неявного `pub get`; `RESOLVE_DEPS=yes` включает его явно, exit 4 означает «не проверено» |
| `scaffold-game-module.py` | неразрушающий скелет собираемого Dart-пакета под жанр |
| `materialize-template-fixtures.py` | создаёт временные pure-Dart, Widgets и Flame проекты для compiler-backed CI шаблонов |
| `validate-levels.py` | schema-driven валидация JSON уровней с эквивалентным dependency-free режимом |
| `dart-doctor.py` | health-check проекта: 8 измерений (архитектура/Dart/перф/kids-safety/a11y/…), PASS/WARN/FAIL, `--only`/`--json`/`--build` |
| `design-doctor.py` | статический UX/a11y/game-design gate: screen map, tap semantics, Reduce Motion, responsive layout, visual states, Flame overlays |
| `flutter-preflight.sh` | gate окружения+git перед сборкой/codegen (`--require`, `--git-clean`); мягкая деградация |
| `safe-run.sh` | fail-closed git-savepoint: атомарный коммит при успехе / откат при провале, без захвата pre-existing edits |
| `triage-log.py` | свод 1000s-строчного Gradle/Xcode/Dart-лога к ~10–25 строкам + вероятные причины |
| `pub-get-if-changed.sh` | пропускает `pub get`, если `pubspec.lock` не менялся (хэш-кэш в `.dart_tool/`) |

---

## Как вызвать

- **Claude Code:** `/dart-mobile-game-studio` (или просто опишите задачу про Flutter/Dart-игру — маршрутизирует [`CLAUDE.md`](CLAUDE.md)).
- **Cursor:** автоматически через `.cursor/rules/dart-mobile-game-studio.mdc` (`alwaysApply: true`); копия навыка — в `.cursor/skills/`.
- **Codex / AGENTS.md-инструменты:** [`AGENTS.md`](AGENTS.md) в корне указывает на навык.

---

## Команды сборки и тестов

Не угадывайте команды — обнаруживайте их через `scripts/verify-flutter-project.sh`. Типовой набор:

```bash
dart pub get             # или: flutter pub get
dart analyze             # статический анализ
dart test                # тесты чистого Dart-ядра (VM, быстро, без устройства)
flutter test             # widget / golden тесты
flutter build appbundle  # релизная сборка под Android
flutter build ipa        # релизная сборка под iOS
```

**Правило честности:** агент сообщает, что analyze/build/тесты прошли, **только** если он реально их
запускал и видел вывод. Если тулчейна здесь нет — он говорит об этом и даёт точные команды.

---

## Разработка навыка

Правьте **только** канонический источник в `.agents/`, затем зеркалируйте в копии инструментов:

```bash
# 1. навык .agents → .claude / .cursor
.agents/skills/dart-mobile-game-studio/scripts/sync-skill.sh
.agents/skills/dart-mobile-game-studio/scripts/sync-skill.sh --check   # CI: упасть, если копии разошлись

# 2. субагенты .agents → .claude / .cursor
.agents/agents/sync-agents.py

# 3. структурный gate (то же, что гоняет CI)
.agents/skills/dart-mobile-game-studio/scripts/validate-skill.sh
```

### CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) гоняет пять gate:
1. **structure** — `validate-skill.sh`: frontmatter, синхронность копий навыка и агентов,
   валидность JSON, документационные пути, синтаксис без bytecode-записи, формат Cursor-глобов и CLI contracts.
2. **cli-contracts** — black-box safety/exit-code/schema/routing suite на Linux и macOS.
3. **ai-routing** — 52 RU/EN сценария, 100% critical cases и полное покрытие workflows/agents.
4. **generated-contracts** — реальный compile/analyze/test pure-Dart, Widgets, Flame шаблонов и
   свежего результата scaffold.
5. **example** — matrix по `examples/memory_match` и `examples/endless_runner`: отдельный
   `dart test` pure core, затем `flutter analyze` + `flutter test` на реальном Flutter SDK.

Отдельный [`release-canary.yml`](.github/workflows/release-canary.yml) еженедельно и при изменениях
примеров собирает оба проекта как Android AAB и unsigned iOS release во временных platform runners.

Оба compiler-backed job также блокируют drift через
`dart format --output=none --set-exit-if-changed .`.

---

## Дорожная карта

**Готово:**
- [x] **21 workflow** — включая локализацию, отладку (`debug-common-errors`), перф-аудит (`run-performance-audit`),
      релиз в оба стора и монетизацию (ads/IAP с гейтом «дети vs 13+»).
- [x] **`scripts/dart-doctor.py`** — health-check проекта по 8 измерениям (протестирован на синтетике).
- [x] **Каталог ошибок** `common-pitfalls.md` + 4 скрипта безопасной автоматизации (preflight, safe-run,
      triage-log, pub-cache) с политикой `ci-and-automation.md`.
- [x] **2 референс-игры** — widgets + Flame: полный lifecycle/pause, responsive shell,
      accessibility, VM-only core tests, dt-clamp, seeded fairness и AABB-коллизии.
- [x] **Compiler-backed CI** — реальные `dart/flutter analyze` + тесты для двух примеров,
      pure-Dart/Widgets/Flame шаблонов и результата scaffold, рядом со структурным и AI-routing gate.
- [x] **Format gate** — официальный Dart formatter проверяет примеры и весь генерируемый код.
- [x] **`LICENSE`** — MIT.
- [x] **9 жанровых дизайн-шаблонов** (`templates/`) — casual, coloring, card, puzzle, platformer-flame,
      endless-runner, quiz, educational-kids, ui-heavy: заполняемый Mini-GDD + архитектурный скелет.
- [x] **Мульти-модельная маршрутизация** — tier-система (8 heavy / 3 medium / 3 light) +
      параллельная оркестрация.

**В работе / опционально:**
- [ ] **GPT-прокси** (опционально) — MCP к OpenAI для реального GPT внутри Claude Code (вариант C мульти-модельной системы).

---

## Дисклеймер

Навык формирует чек-листы и списки рисков — это **не** юридическая консультация и **не** гарантия
одобрения в App Store или Google Play. Материальные и спорные вопросы по приватности/комплаенсу
маршрутизируйте на роли `legal-compliance` / `security-auditor` и к квалифицированному юристу.
Никаких сторонних копирайт-ассетов: только плейсхолдерная векторная графика или ассеты пользователя.
