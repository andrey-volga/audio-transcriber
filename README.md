# audio-transcriber

Локальная транскрибация аудио/видео-файлов в текст с помощью Whisper (CPU, оффлайн) с последующей очисткой через DeepSeek.

## Установка

```bash
uv sync
```

**Системная зависимость:** требуется установленный `ffmpeg`.

**Для очистки текста через DeepSeek** — добавить API-ключ:

```bash
echo 'DEEPSEEK_API_KEY=sk-...' >> ~/.config/audio-transcriber/.env
```

---

## Использование

### `transcribe` — транскрибация файлов

```
uv run transcribe [SOURCE] [OPTIONS]
```

| Аргумент/Флаг | Краткий | Описание | Умолчание |
|---|---|---|---|
| `SOURCE` | — | Путь к аудио/видео файлу или директории | Из конфига (`default_source`) |
| `--output DIR` | `-o` | Куда сохранять сырые `.md` файлы | Из конфига (`default_output`) или рядом с исходником |
| `--model MODEL` | `-m` | Размер модели: `tiny`, `base`, `small`, `medium`, `large` | Из конфига или `base` |
| `--lang LANG` | `-l` | Код языка: `ru`, `en`, ... | `ru` |

После транскрибации каждый файл проходит через DeepSeek и сохраняется отдельно:

```
✓ interview.mp3 → /RawText/[2026-03-11 interview].md
  ✦ очищено → /Transcribes/[2026-03-11 interview].md
```

Если DeepSeek недоступен — сырой текст всё равно сохраняется, очищенный файл содержит пометку об ошибке и исходный текст:

```
✓ interview.mp3 → /RawText/[2026-03-11 interview].md
  ⚠ не очищено (ошибка API) → /Transcribes/[2026-03-11 interview].md
```

**Примеры:**

```bash
# Один файл
uv run transcribe recording.mp3

# Папка целиком, английский, крупная модель
uv run transcribe ~/recordings --model large --lang en

# Указать папку вывода
uv run transcribe ~/recordings -o ~/transcripts
```

---

### `transcribe watch` — мониторинг папки

Следит за папкой и автоматически транскрибирует новые файлы. Работает до `Ctrl+C`. Состояние сохраняется между перезапусками — уже обработанные файлы повторно не транскрибируются. Дедупликация по содержимому файла (не по имени).

```
uv run transcribe watch [SOURCE] [OPTIONS]
```

| Аргумент/Флаг | Краткий | Описание | Умолчание |
|---|---|---|---|
| `SOURCE` | — | Папка для мониторинга | Из конфига (`default_source`) |
| `--model MODEL` | `-m` | Размер модели Whisper | Из конфига или `base` |
| `--lang LANG` | `-l` | Код языка | `ru` |

Интервал проверки берётся из конфига (`monitor_interval`, по умолчанию 10 сек).

Остановить: `Ctrl+C` — завершается в течение 500 мс.

```bash
pkill -f "transcribe watch"
```

**Пример:**

```bash
uv run transcribe watch ~/incoming --model small
```

---

### `transcribe polish` — очистка текста через DeepSeek

Прогоняет уже готовый `.md` файл (или все файлы в папке) через DeepSeek.

```
uv run transcribe polish [SOURCE] [--output PATH]
```

| Аргумент/Флаг | Краткий | Описание | Умолчание |
|---|---|---|---|
| `SOURCE` | — | Файл или папка с `.md` файлами | Из конфига (`default_output`) |
| `--output PATH` | `-o` | Куда сохранить результат | Из конфига (`polish_output`) |

**Примеры:**

```bash
# Очистить все файлы из default_output → в polish_output
uv run transcribe polish

# Один файл
uv run transcribe polish ~/RawText/note.md

# Вся папка
uv run transcribe polish ~/RawText/

# Указать куда сохранить
uv run transcribe polish note.md --output ~/clean/note.md
```

---

### `transcribe-config` — управление конфигурацией

Конфиг хранится в `~/.config/audio-transcriber/config.toml`.

| Команда | Описание |
|---|---|
| `set-source PATH` | Папка с аудио по умолчанию |
| `set-output PATH` | Папка для сырых транскрипций |
| `set-polish-output PATH` | Папка для очищенных транскрипций |
| `set-raw-done PATH` | Куда перемещать сырой текст после успешной полировки |
| `show` | Показать конфиг и эффективные значения |

```bash
uv run transcribe-config set-source ~/pipeline/inbox
uv run transcribe-config set-output ~/pipeline/raw
uv run transcribe-config set-polish-output ~/pipeline/notes
uv run transcribe-config set-raw-done ~/pipeline/raw/Done
uv run transcribe-config show
```

---

## Конфигурация

Файл: `~/.config/audio-transcriber/config.toml`

| Ключ | Тип | Описание | Умолчание |
|---|---|---|---|
| `default_source` | строка (путь) | Папка с аудио по умолчанию | — |
| `default_output` | строка (путь) | Папка для сырых `.md` файлов | рядом с исходником |
| `polish_output` | строка (путь) | Папка для очищенных `.md` файлов | `~/Obsidian/00. Inbox/Transcribes` |
| `deepseek_model` | строка | Модель DeepSeek для очистки | `deepseek-chat` |
| `default_model` | строка | Модель Whisper: `tiny`, `base`, `small`, `medium`, `large` | `base` |
| `after_transcription` | строка | Что делать с аудио после транскрибации: `keep`, `delete`, `move` | `keep` |
| `processed_folder` | строка (путь) | Куда перемещать аудио при `after_transcription = "move"` | — |
| `raw_done_folder` | строка (путь) | Куда перемещать сырой текст после успешной полировки | — |
| `monitor_interval` | число | Интервал проверки папки в секундах (`watch`) | `10` |
| `log_path` | строка (путь) | Путь к файлу лога | `~/.config/audio-transcriber/transcriber.log` |
| `log_max_bytes` | число | Максимальный размер лога в байтах (ротация по размеру) | `10485760` (10 МБ) |

**Пример:**

```toml
default_source = "/home/user/recordings"
default_output = "/home/user/RawText"
polish_output = "/home/user/Obsidian/Inbox/Transcribes"
deepseek_model = "deepseek-chat"
default_model = "small"
after_transcription = "move"
processed_folder = "/home/user/recordings/done"
monitor_interval = 30
```

API-ключ DeepSeek хранится отдельно в `~/.config/audio-transcriber/.env`:

```
DEEPSEEK_API_KEY=sk-...
```

---

## Логирование

События записываются в лог-файл в формате plain text, одна запись на строку:

```
2026-03-11 14:23:00 WATCH_START pid=12345 source=/home/user/recordings
2026-03-11 14:23:15 FILE_START pid=12345 file=interview.mp3
2026-03-11 14:24:32 FILE_DONE pid=12345 file=interview.mp3 audio=00:45:12 started=2026-03-11 14:23:15 finished=2026-03-11 14:24:32 output=/RawText/[2026-03-11 interview].md
2026-03-11 14:30:00 WATCH_STOP pid=12345
```

| Событие | Описание |
|---|---|
| `TRANSCRIBE_START` | Запуск команды `transcribe` |
| `TRANSCRIBE_DONE` | Завершение команды `transcribe` |
| `WATCH_START` | Запуск команды `watch` |
| `WATCH_STOP` | Остановка `watch` |
| `FILE_START` | Начало обработки файла |
| `FILE_DONE` | Успешная транскрибация |
| `FILE_ERROR` | Ошибка обработки файла |

Ротация: при достижении `log_max_bytes` создаётся до 3 резервных копий (`.log.1`, `.log.2`, `.log.3`).

---

## Поддерживаемые форматы

`MP3`, `WAV`, `MP4`, `M4A`, `OGG`, `FLAC`
