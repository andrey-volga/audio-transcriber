# Audio Transcriber — описание системы

## Назначение

CLI-инструмент для локальной транскрибации аудио/видео-файлов в текст (Whisper, CPU, оффлайн) с последующей очисткой через DeepSeek.

---

## Функциональные требования

### FR-01: Входные данные
- Форматы: **MP3, WAV, MP4, M4A, OGG, FLAC**
- Источники:
  - Один файл: `transcribe audio.mp3`
  - Папка (batch): `transcribe ./recordings/` — все аудио-файлы в директории

### FR-02: Транскрибация
- Движок: **faster-whisper** (локальный, CPU, int8)
- Язык по умолчанию: `ru` (настраивается через `--lang`)
- Модели: `tiny`, `base`, `small`, `medium`, `large` (настраивается через `--model` или конфиг)
- Вывод: чистый текст без таймкодов, в формате `.md`

### FR-03: Очистка через DeepSeek
- После транскрибации текст автоматически прогоняется через `deepseek-chat`
- Промпт: исправление речевых артефактов, грамматики, форматирование
- При недоступности API: сырой файл сохраняется, очищенный содержит пометку об ошибке + исходный текст
- Максимум 8192 токена на ответ

### FR-04: Мониторинг папки (`watch`)
- Периодически сканирует папку, автоматически обрабатывает новые файлы
- Дедупликация по SHA-256 хэшу первых 64KB (не по имени файла)
- Персистентность через SQLite: состояние сохраняется между перезапусками
- Retry для упавших заданий: при краше процесса файлы переобрабатываются при следующем запуске
- Статусы заданий: `processing` → `done` / `error`

### FR-05: Постобработка файлов
- После успешной транскрибации с исходным аудио можно:
  - `keep` — оставить на месте (по умолчанию)
  - `delete` — удалить
  - `move` — переместить в `processed_folder`

### FR-06: Конфигурация
- Хранится в `~/.config/tool-audio/config.toml`
- Управляется через `transcribe-config set-source|set-output|set-polish-output|show`
- API-ключ DeepSeek: `~/.config/tool-audio/.env`

### FR-07: Логирование
- Файл: `~/.config/tool-audio/tool-audio.log`
- Ротация: до 3 резервных копий при достижении лимита размера (по умолчанию 10 МБ)
- События: `WATCH_START`, `WATCH_STOP`, `FILE_START`, `FILE_DONE`, `FILE_ERROR`, `TRANSCRIBE_START`, `TRANSCRIBE_DONE`

---

## Нефункциональные требования

- Платформа: Linux, Python 3.13
- Системная зависимость: `ffmpeg`
- Работа без GPU (только CPU)
- Не требует интернета для транскрибации (только для DeepSeek)
- Batch-режим продолжает работу при ошибке отдельного файла

---

## Ограничения текущей версии

- Один рабочий поток: файлы обрабатываются последовательно
- SQLite достаточно до ~1000 заданий/день (фаза 0)
- Нет HTTP API, веб-интерфейса, диаризации, субтитров (SRT), URL/YouTube

---

## Структура проекта

```
tool-audio/
├── docs/
│   └── requirements.md        # этот файл
├── src/
│   └── tool_audio/
│       ├── cli.py             # CLI (Typer): main, watch, polish, config
│       ├── transcriber.py     # faster-whisper, model cache
│       ├── utils.py           # форматы, сканирование, output path, file actions
│       ├── storage.py         # SQLite job store (~/.config/.../jobs.db)
│       ├── polisher.py        # DeepSeek API, промпт
│       ├── config.py          # TOML конфиг
│       └── prompts/
│           └── polish_prompt.md
├── tests/
│   ├── test_cli.py
│   └── test_utils.py
├── pyproject.toml
├── CLAUDE.md
└── README.md
```

---

## Зависимости

| Пакет | Назначение |
|-------|-----------|
| `faster-whisper` | Движок транскрибации (CPU, int8) |
| `typer` | CLI-интерфейс |
| `rich` | Форматированный вывод в терминал |
| `openai` | Клиент для DeepSeek API (OpenAI-совместимый) |
| `python-dotenv` | Чтение `.env` для API-ключа |
| `pytest`, `pytest-mock` | Тестирование |

Системная зависимость: **ffmpeg**

---

## Дорожная карта

| Фаза | Статус | Описание |
|------|--------|---------|
| 0 | ✅ Готово | SQLite job store, персистентность watch, дедупликация по хэшу |
| 1 | Planned | Разделение Watcher/Worker, параллельная обработка |
| 2 | Planned | HTTP API (FastAPI), Node Protocol |
| 3 | Planned | Pipeline Engine (YAML-пайплайны) |
| 4 | Planned | Распределённые воркеры (Redis) |
