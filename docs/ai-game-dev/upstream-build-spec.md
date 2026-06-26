# Upstream build spec — "AI Game Builder Skill for Dart & Flutter"

Full, verbatim capture of the user-provided spec (PDF, 2026-06). This is the authoritative
requirements doc for building out `dart-mobile-game-studio`. Nothing here is dropped; every source
URL and instruction is preserved. The build is an **incremental enhancement** of the existing
minimal skill — audit first, preserve working parts, add missing modules, do not duplicate, never
rewrite wholesale, and list all changes at the end.

---

## Задача
Доработать существующий минимальный AI Skill для разработки игр на Dart и Flutter. Не создавать с
нуля — проанализировать текущую структуру, сохранить рабочие части и расширить до production-grade
skill для игр и игровых приложений на Dart + Flutter под **iOS, iPadOS и Android**. Работать
аккуратно: не ломать архитектуру, не удалять полезные файлы, не переписывать всё. Сначала аудит,
потом улучшения.

## 1. Главная цель
Расширить минимальный skill до уровня **AI Game Builder Skill for Dart & Flutter**, помогающий агенту:
- проектировать игры и игровые приложения;
- выбирать архитектуру под конкретный тип игры;
- писать production-ready Dart/Flutter код;
- использовать Flutter SDK, Dart SDK, Flame Engine и официальные best practices;
- создавать UI, анимации, игровые экраны, меню, onboarding, настройки, магазин и overlay;
- работать с ассетами, спрайтами, аудио, responsive layout и адаптацией под планшеты;
- добавлять монетизацию: ads, rewarded ads, in-app purchases, subscriptions;
- писать unit, widget, integration и E2E-тесты;
- оптимизировать производительность через Flutter DevTools;
- готовить проект к публикации в App Store и Google Play.

## 2. Обязательный порядок работы
Сначала аудит: изучи файлы и структуру; определи полезные части для сохранения; найди пробелы
(архитектура, workflow, templates, checklists, package policy, release, monetization, testing, Flame
Engine); составь краткий план; только потом вноси изменения. **Инкрементально, не разрушительно.**

## 3. Источники для изучения и интеграции
Перечисленные ниже репозитории/документацию **нельзя просто вставить списком** — нужно превратить их
в конкретные инструкции, workflow, policies, templates и checklists.

## 4. Готовые AI skills (основа для структуры, progressive disclosure, агентных workflow)
- https://github.com/flutter/skills
- https://github.com/dart-lang/skills

## 5. Официальные Flutter и Dart источники (canonical knowledge base)
- https://github.com/flutter/flutter
- https://github.com/dart-lang/sdk
- https://github.com/dart-lang/language
- https://docs.flutter.dev/
- https://dart.dev/

Skill должен учитывать: Flutter architecture; Dart language rules; null safety; async/await; streams;
isolates; widgets; state management; navigation; animations; accessibility; localization; platform
integration; testing; performance; deployment; package management.

## 6. Инструменты разработчика и официальные примеры
- https://github.com/flutter/devtools
- https://github.com/flutter/games
- https://github.com/flutter/packages
- https://github.com/flutter/cocoon
- https://github.com/flutter/codelabs
- https://github.com/flutter/genui
- https://github.com/dart-lang/build
- https://github.com/dart-lang/dart_style
- https://github.com/dart-lang/dartdoc
- https://github.com/dart-lang/samples
- https://github.com/flutter/samples
- https://github.com/flutter/demos

Особенно важны workflow по: созданию Flutter game project; использованию Flutter game templates;
profiling через Flutter DevTools; анализу rebuild/memory/frame rendering; build_runner; форматированию
кода; генерации документации.

## 7. Flame Engine (обязательный игровой слой, отдельный модуль)
- https://github.com/flame-engine/flame
- https://docs.flame-engine.org/

Skill должен определять, когда нужен Flame, а когда достаточно обычного Flutter UI. Flame для:
game loop; sprites; components; collision detection; camera; world system; particles; effects;
gestures; input handling; overlays; pause/resume; audio; level system; entity/component structure.

## 8. Алгоритмы и игровая логика
- https://github.com/TheAlgorithms/Dart

Reference для: pathfinding; sorting; graph algorithms; randomization; procedural generation; scoring
systems; board/grid logic; puzzle mechanics; utility algorithms.

## 9. Обучающие материалы (слой объяснений и onboarding)
- https://github.com/smartherd/DartTutorial
- https://github.com/VadimYakovliev/flutter-knowledge
- https://education.yandex.ru/handbook/flutter/article/dart-oop
- https://habr.com/ru/companies/friflex/articles/819503/
- https://www.codeporting.ai/ru/language/dart

Skill должен уметь не только писать код, но и объяснять решения понятным языком для команды.

## 10. Пакеты и экосистема
- https://pub.dev/packages?q/
- https://github.com/dart-lang/labs
- https://github.com/dart-lang/native
- https://github.com/dart-lang/test
- https://github.com/dart-lang/tools
- https://github.com/dart-lang/ecosystem
- https://github.com/dart-lang/ai
- https://github.com/dart-lang/core
- https://github.com/flutter/core-packages
- https://github.com/Hamed233/Awesome-Flutter-Packages

Добавь/усиль модуль **package-selection-policy**. Правила: (1) сначала официальные Flutter/Dart
пакеты; (2) потом mature community packages с хорошей поддержкой; (3) не добавлять зависимость, если
задача решается стандартным Flutter API; (4) для каждой зависимости агент обязан объяснять: зачем
нужна; есть ли official alternative; риски поддержки; влияние на размер приложения; подходит ли для
iOS, iPadOS и Android.

## 11. UI, виджеты и анимации
- https://github.com/MinaFaried3/Flutter-Animation
- https://github.com/bizz84/flutter_animations_gallery
- https://github.com/lohanidamodar/flutter_ui_challenges
- https://github.com/flutterfx/flutterfx_widgets
- https://docs.flutter.dev/ui/widgets/material
- https://docs.flutter.dev/ui/widgets/cupertino
- https://github.com/florent37/Flutter-Anim
- https://docs.flutter.dev/ui/widgets/animation

Skill должен помогать создавать: game main menu; start screen; victory/defeat screen; settings
screen; shop UI; inventory UI; level selection; onboarding; animated buttons; transitions;
responsive UI; iOS-style Cupertino UI; Android-style Material UI; UI для iPhone, iPad и Android tablets.

## 12. Production-примеры Flutter-приложений (quality reference)
- https://github.com/gskinnerTeam/flutter-wonderous-app
- https://github.com/flutter/demos
- https://github.com/flutter/samples
- https://itsallwidgets.com/

Для улучшения: архитектуры; навигации; визуального качества; анимаций; структуры проекта; responsive
layout; production UX.

## 13. Кодогенерация и boilerplate
Workflow для: **json_serializable; freezed; auto_route; build_runner.**
Генерировать boilerplate для: models; DTO; entities; repositories; services; routes; screens;
controllers; providers; game state; save/load system; settings; localization.

## 14. Монетизация и релиз
- https://flutter.dev/monetization
- https://docs.flutter.dev/cookbook/plugins/google-mobile-ads
- https://docs.flutter.dev/resources/in-app-purchases-overview
- https://docs.flutter.dev/deployment/android
- https://docs.flutter.dev/deployment/ios
- https://developer.apple.com/documentation/
- https://developers.google.com/android-publisher/api-ref/rest?hl=ru

Skill помогает с: banner ads; interstitial ads; rewarded ads; in-app purchases; subscriptions;
premium unlock; remove ads purchase; consumable purchases; non-consumable purchases; soft currency;
hard currency; rewarded progression; App Store Connect; TestFlight; Google Play Console; internal
testing; closed testing; production release; signing; bundle identifier; versioning; privacy policy;
app metadata.

## 15. Тестирование и production quality — Patrol
- https://github.com/leancodepl/patrol
- https://patrol.leancode.co/

Проектировать/писать: unit; widget; integration; E2E; golden; smoke; regression. E2E покрывает:
onboarding; login; purchase flow; rewarded ads flow; game start; level completion; pause/resume;
settings; permissions; native dialogs; app lifecycle; iOS/Android platform interactions.

## 16. Рекомендуемая структура skill (добавить недостающее, не дублировать существующее)
```
flutter-dart-game-dev-skill/
  SKILL.md
  references.md
  architecture.md
  package-policy.md
  quality-policy.md
  monetization-policy.md
  release-policy.md
  workflows/
    create-new-game.md
    choose-game-architecture.md
    setup-flutter-project.md
    setup-flame-project.md
    add-game-loop.md
    add-level-system.md
    add-animations.md
    add-assets-pipeline.md
    add-audio.md
    add-state-management.md
    add-navigation.md
    add-save-system.md
    add-monetization.md
    add-in-app-purchases.md
    add-ads.md
    write-tests.md
    run-performance-audit.md
    prepare-ios-release.md
    prepare-android-release.md
    debug-common-errors.md
  templates/
    casual-game.md
    coloring-game.md
    card-game.md
    puzzle-game.md
    platformer-flame.md
    endless-runner.md
    quiz-game.md
    educational-kids-game.md
    ui-heavy-game.md
  checklists/
    dart-code-quality.md
    flutter-ui-quality.md
    game-architecture.md
    flame-quality.md
    performance.md
    accessibility.md
    localization.md
    monetization.md
    app-store-release.md
    google-play-release.md
    testing.md
```

## 17. Важное правило по существующему skill
Не создавай параллельную новую структуру, если skill уже имеет свою организацию. Если файл есть —
улучши; если модуля нет — добавь; если структура отличается — адаптируй рекомендации под текущую
архитектуру; при конфликте — сохрани текущую рабочую логику, но усиль её; не удаляй существующие
правила без причины. В конце покажи список всех внесённых изменений.

## 18. Обязательные workflow после доработки
**18.1 Создание новой игры:** определить тип игры; решить Flame vs Flutter UI; предложить
архитектуру; создать структуру проекта; настроить зависимости; добавить базовые экраны; game state;
assets pipeline; тесты; performance checklist.
**18.2 Выбор архитектуры:** чистый Flutter UI; Flutter + CustomPainter; Flutter + Flame; Flutter +
backend; Flutter + Firebase/Supabase; offline-first architecture.
**18.3 Добавление игровой механики:** уровни; очки; прогрессия; достижения; таймеры; инвентарь;
предметы; drag-and-drop; collision; movement; camera; save/load; difficulty curve.
**18.4 Оптимизация производительности:** стабильность 60 FPS; jank; rebuild problems; image size;
shader compilation; memory leaks; unnecessary widgets; excessive package usage; animation performance;
Flame component lifecycle.
**18.5 Подготовка к релизу:** app icon; splash screen; package name; bundle identifier; signing;
permissions; privacy policy; app metadata; screenshots; TestFlight; Google Play internal testing;
release build; crash reporting; analytics.

## 19. Требования к качеству кода и решений
Код/инструкции должны быть: production-ready; readable; modular; maintainable; testable; null-safe;
compatible with `flutter analyze`; formatted через `dart format`; без случайных зависимостей; с ясным
разделением UI, business logic и game logic; адаптированы под iOS, iPadOS и Android.
**Запрещено:** переписывать skill полностью без необходимости; удалять полезные правила; писать
хаотичные инструкции; добавлять ссылки без объяснения их использования; добавлять пакеты без package
policy; игнорировать testing/performance/monetization/release; смешивать Flutter UI и Flame без
decision rules.

## 20. Формат итогового результата
Выдать: (1) краткий аудит текущего skill; (2) найденные пробелы; (3) изменённые файлы; (4)
добавленные файлы; (5) усиленные workflow; (6) интегрированные источники; (7) принятые архитектурные
решения; (8) инструкцию по использованию обновлённого skill; (9) список следующих улучшений за рамками
текущей доработки.

## 21. Главный принцип
Skill должен работать как **senior Flutter/Dart game development architect**, ведя агента по циклу:
`idea → audit → architecture → prototype → production code → testing → optimization → monetization →
release`. Цель — превратить минимальный skill в мощный production-ready AI Skill для коммерческих игр
на Flutter.

---

# Source → integration map (sources become instructions, not a list) — §3 requirement

Every source above is turned into a concrete skill artifact. Status fills in as the build proceeds
("done" = the source's guidance is embedded in that artifact).

| Source(s) | Becomes (skill artifact) | Status |
|---|---|---|
| flutter/skills, dart-lang/skills | progressive-disclosure structure (SKILL.md → references → workflows/checklists) + agent workflows | in progress |
| flutter/flutter, dart-lang/sdk, dart-lang/language, docs.flutter.dev, dart.dev | references/dart/* + flutter-game-architecture.md (null-safety, async, streams, isolates, widgets, state mgmt, navigation, a11y, localization, perf, deployment) | partial (dart refs pending) |
| flutter/games (Casual Games Toolkit) | references/flutter-games-toolkit.md + create-new-game / setup-flutter-project workflows | pending |
| flutter/devtools | run-performance-audit workflow + performance-checklist.md (rebuild/memory/frame analysis) | partial |
| flutter/packages, dart-lang/{labs,native,test,tools,ecosystem,ai,core}, flutter/core-packages, Awesome-Flutter-Packages, pub.dev | references/package-policy.md | DONE |
| flame-engine/flame + docs.flame-engine.org | flutter-flame-patterns.md (Flame module) + setup-flame-project / add-game-loop / add-level-system + checklists/flame-quality | partial |
| TheAlgorithms/Dart | references/algorithms-for-games.md (pathfinding/sorting/graph/proc-gen/scoring/grid/puzzle) | pending |
| DartTutorial, flutter-knowledge, yandex handbook, habr, codeporting | onboarding/explanation layer in references + narrative-writer agent ("explain to the team") | pending |
| dart-lang/{build,dart_style,dartdoc} | codegen workflow (build_runner/json_serializable/freezed/auto_route) + format/doc gates | pending |
| Flutter-Animation, flutter_animations_gallery, flutter_ui_challenges, flutterfx_widgets, Flutter-Anim, material/cupertino/animation docs | references/ui-and-animations.md + ui-heavy-game template + add-animations workflow | pending |
| wonderous-app, flutter/demos, flutter/samples, itsallwidgets | references/production-quality.md (architecture/nav/responsive/UX) | pending |
| flutter/monetization, google-mobile-ads, in-app-purchases, deployment/{android,ios}, Apple/Google publisher | references/monetization-policy.md + release-policy.md + add-ads/add-iap/prepare-*-release workflows | DONE (policies) |
| leancodepl/patrol | write-tests workflow (Patrol E2E) + checklists/testing.md + qa-tester agent | pending |
| flutter/cocoon, flutter/genui, dart-lang/{ai,native} | noted; not core to a 2D game skill — referenced where relevant, not forced | noted |
