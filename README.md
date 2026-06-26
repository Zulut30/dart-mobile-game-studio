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
│  ├─ references/   (18 файлов)              ← пайплайн, архитектура, Flame, a11y, тесты, перф…
│  │  └─ dart/      (7 файлов)               ← «мастерство Dart» (как писать отличный Dart)
│  ├─ workflows/    (13 файлов)              ← пошаговые playbook'и (создать игру, добавить уровни…)
│  ├─ checklists/   (11 файлов)              ← tick-листы для ревьюера/агента по каждой области
│  ├─ assets/       (8 файлов)               ← шаблоны: GDD, JSON-схема уровня, Flame/Widget-шаблоны,
│  │                                            seeded RNG, строгий analysis_options, чек-листы
│  └─ scripts/      (5 файлов)               ← sync, validate, verify-flutter-project, scaffold, levels
├─ .agents/agents/  (14 ролей + README)      ← КАНОНИЧЕСКИЕ субагенты + sync-agents.py
├─ .claude/skills/…  .claude/agents/         ← зеркала для Claude Code   (синхронизируются)
├─ .cursor/skills/…  .cursor/rules/agents/   ← зеркала для Cursor        (синхронизируются)
├─ .cursor/rules/                            ← Cursor .mdc-правила (общее / архитектура / тесты)
├─ docs/ai-game-dev/upstream-build-spec.md   ← полная исходная спецификация (21 раздел)
├─ examples/                                 ← (в работе) рабочая референс-игра: ядро + Flutter-UI
├─ .github/workflows/ci.yml                  ← CI: структурный gate (без Dart-тулчейна)
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
зеркалируются в `.claude/agents/` и `.cursor/rules/agents/`). Субагенты не могут вызывать друг друга,
поэтому `game-coordinator` возвращает план делегирования, который главный поток выполняет по шагам.

- **Сборка:** `game-coordinator` (PM/декомпозиция) → `game-designer` → `engine-architect` →
  `gameplay-programmer` (+ параллельно `art-director`, `narrative-writer`, `balance-economist`) → `qa-tester`.
- **Ревью и аудит (read-only):** `code-reviewer` (по диффу/PR), а перед релизом — «гейт»:
  `code-auditor` (вся кодовая база), `security-auditor`, `performance-auditor`, `legal-compliance`.
- **Релиз:** `release-engineer` — готовность к подаче в **App Store** *и* **Google Play**.

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
`codegen-and-boilerplate` · `testing-e2e-patrol`.

### `references/dart/` — мастерство Dart
`README` (планка качества — начните отсюда) · `dart-language-essentials` · `dart-async-isolates` ·
`dart-api-design` · `flutter-widgets-mastery` · `dart-memory-performance` · `dart-patterns-idioms`.

### Политики (правила, которые применяют агенты) — `references/`
`package-policy` (порядок выбора зависимостей) · `quality-policy` (планка продакшен-качества) ·
`monetization-policy` (реклама/IAP/подписки с гейтом «дети vs 13+») · `release-policy` (правила подачи
в оба стора и ловушки отклонения).

### `checklists/` — tick-листы для ревью
`dart-code-quality` · `flutter-ui-quality` · `game-architecture` · `flame-quality` · `performance` ·
`accessibility` · `localization` · `monetization` · `app-store-release` · `google-play-release` · `testing`.

### `workflows/` — пошаговые playbook'и
`create-new-game` · `choose-game-architecture` · `setup-flutter-project` · `setup-flame-project` ·
`add-game-loop` · `add-level-system` · `add-animations` · `add-assets-pipeline` · `add-audio` ·
`add-state-management` · `add-navigation` · `add-save-system` · `write-tests`.

---

## Шаблоны и скрипты

**`assets/` (копировать и адаптировать):** `gdd-template.md`, `level-schema-template.json`
(JSON-схема Draft-07 для данных уровня), `flame_game_template.dart`, `flutter_game_widget_template.dart`,
`seeded_random.dart`, `analysis_options.yaml` (строгие линты), `review-checklist.md`, `privacy-checklist.md`.

**`scripts/`:**

| Скрипт | Назначение |
|---|---|
| `sync-skill.sh` | зеркалирует канонический навык в `.claude/` и `.cursor/` (`--check` для CI) |
| `validate-skill.sh` | структурный gate: frontmatter, синхронность копий, валидность JSON, синтаксис скриптов |
| `verify-flutter-project.sh` | находит Flutter/Dart-проект и запускает `dart analyze` + тесты |
| `scaffold-game-module.py` | неразрушающий скелет собираемого Dart-пакета под жанр |
| `validate-levels.py` | валидация JSON уровней против `level-schema-template.json` |

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

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) сейчас гоняет **только структурный gate**
(`validate-skill.sh`): frontmatter и `name == имя папки`, синхронность копий навыка и агентов,
валидность JSON, синтаксис bash/python, формат Cursor-глобов. Чистый python/bash — **Dart-тулчейн не
нужен**, поэтому CI стабильно зелёный. Dart-гейты (`dart format`/`analyze`/`test`, Patrol) будут
добавлены вместе с примером игры, чтобы их можно было проверить end-to-end.

---

## Дорожная карта (в работе)

Базис навыка готов и запушен. Доводится до полного «production»:

- [ ] **7 workflow'ов:** `debug-common-errors`, `prepare-ios-release`, `prepare-android-release`,
      `add-monetization`, `add-ads`, `add-in-app-purchases`, `run-performance-audit`.
- [ ] **9 шаблонов дизайна игр:** casual, coloring, card, puzzle, platformer-flame, endless-runner,
      quiz, educational-kids, ui-heavy.
- [ ] **`scripts/dart-doctor.py`** — CLI проверки здоровья проекта (аналог `flutter doctor`, но про
      *качество проекта*: окружение, архитектура, качество Dart, перф, kids-safety, a11y, сборка/тесты).
- [ ] **`examples/`** — полная собираемая и протестированная референс-игра (чистое Dart-ядро + Flutter-UI).
- [ ] **Dart CI** — добавить job `dart format`/`analyze`/`dart test` (через `dart-lang/setup-dart`) рядом с примером.
- [ ] **`LICENSE`** — добавить файл лицензии.

---

## Дисклеймер

Навык формирует чек-листы и списки рисков — это **не** юридическая консультация и **не** гарантия
одобрения в App Store или Google Play. Материальные и спорные вопросы по приватности/комплаенсу
маршрутизируйте на роли `legal-compliance` / `security-auditor` и к квалифицированному юристу.
Никаких сторонних копирайт-ассетов: только плейсхолдерная векторная графика или ассеты пользователя.
