# Архитектура — tool-audio

Python CLI для оффлайн-транскрибации аудио/видео с помощью Whisper.

## Стек

- Python 3.13 + uv
- `faster-whisper` — CPU-only, int8 квантизация
- `typer` — CLI
- `rich` — прогресс-бар и логи
- SQLite — хранение заданий (`~/.config/tool-audio/jobs.db`)
- DeepSeek API — постобработка текста (polisher)

## Слои

```
cli.py           ← точка входа, Typer-команды: main / watch / polish / config
transcriber.py   ← обёртка faster-whisper, кеш модели в памяти (_model_cache)
utils.py         ← определение аудиофайлов, сканирование директорий, пути вывода
storage.py       ← SQLite job store, дедупликация по SHA-256 первых 64KB
polisher.py      ← DeepSeek API (OpenAI-совместимый клиент), полировка текста
config.py        ← TOML конфиг (~/.config/tool-audio/config.toml)
```

## Ключевые решения

- Язык по умолчанию — русский (`ru`)
- Вывод — `.md` файлы, имя из mtime файла (`YYYY-MM-DD stem.md`)
- `watch` режим — персистентный через SQLite, пропускает уже обработанные файлы
- Зависания `processing` при перезапуске сбрасываются в `error`
