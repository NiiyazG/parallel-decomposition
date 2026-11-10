# Parallel Decomposition for Hermes Agent

Проверяемая оркестрация сложных задач: планирование DAG, immutable snapshots, реальные вызовы `delegate_task`, приёмка артефактов и финальная интеграция.

## Установка

Скопируйте каталог `parallel-decomposition` в `$HERMES_HOME/skills/` (на Windows обычно `%LOCALAPPDATA%\\hermes\\skills\\`). Скилл не требует сторонних Python-пакетов и совместим с Python 3.9+.

## Быстрый smoke-test

```bash
cd parallel-decomposition
python scripts/create_snapshot.py --out examples/snapshot --input examples/inputs/brief.txt
python scripts/validate_plan.py examples/plan.example.json --dag examples/dag.example.json --check-snapshot
python -m unittest discover -s tests -v
```

Snapshot намеренно одноразовый: команда откажется перезаписывать непустой каталог. Для нового запуска создайте новый каталог или новую версию входов.

## Что внутри

- `SKILL.md` — операционный контракт для Hermes.
- `scripts/create_snapshot.py` — копирование входов и SHA-256 manifest.
- `scripts/validate_plan.py` — проверка контрактов, ресурсов, циклов и волн DAG.
- `scripts/validate_results.py` — формальная приёмка результатов и артефактов.
- `templates/delegate-output.schema.json` — единый JSON-контракт ответа субагента.
- `examples/` — минимальный воспроизводимый пример.
- `tests/` — тесты валидаторов и fail-closed поведения.

## Важные границы

Скрипты не вызывают LLM и не подтверждают семантическое качество отчётов. Делегирование выполняет родительский Hermes через `delegate_task`; родитель обязан проверить фактические файлы, тесты и разрешения перед статусом `DONE`. Snapshot не является Git worktree и не заменяет проверку версии удалённой системы.

Публикация, деплой, удаление, платежи, изменения БД и другие внешние записи требуют отдельного явного разрешения пользователя. `requires_approval: true` только блокирует автоматический запуск — это не авторизация.

## Лицензия

MIT. См. `LICENSE`.
