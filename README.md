# audio-transcriber

Локальная транскрибация аудио/видео-файлов в текст с помощью Whisper (CPU, оффлайн).

## Установка

```bash
uv sync
```

**Системная зависимость:** требуется установленный `ffmpeg`.

## Использование

### `transcribe` — транскрибация файлов

```
uv run transcribe [SOURCE] [OPTIONS]
```

| Аргумент/Флаг | Краткий | Описание | Умолчание |
|---|---|---|---|
| `SOURCE` | — | Путь к аудио/видео файлу или директории | Из конфига (`default_source`) |
| `--output DIR` | `-o` | Куда сохранять `.md` файлы | Из конфига или рядом с исходником |
| `--model MODEL` | `-m` | Размер модели: `tiny`, `base`, `small`, `medium`, `large` | Из конфига или `base` |
| `--lang LANG` | `-l` | Код языка: `ru`, `en`, ... | `ru` |

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

Следит за папкой и автоматически транскрибирует новые файлы. Работает до `Ctrl+C`.

```
uv run transcribe watch [SOURCE] [OPTIONS]
```

| Аргумент/Флаг | Краткий | Описание | Умолчание |
|---|---|---|---|
| `SOURCE` | — | Папка для мониторинга | Из конфига (`default_source`) |
| `--model MODEL` | `-m` | Размер модели Whisper | Из конфига или `base` |
| `--lang LANG` | `-l` | Код языка | `ru` |

Интервал проверки берётся из конфига (`monitor_interval`, по умолчанию 10 сек).

Для каждого обработанного файла выводится:

```
✓ interview.mp3 → /transcripts/[2026-03-11 interview].md
  audio: 00:45:12  |  2026-03-11 14:23:15 → 2026-03-11 14:24:32
```

- **audio** — длительность аудиофайла (из конца последнего сегмента Whisper)
- **start → finish** — время начала и окончания транскрибации

Остановить: `Ctrl+C` — завершается в течение 500 мс.

Чтобы остановить уже запущенный фоновый процесс:

```bash
pkill -f "transcribe watch"
```

**Пример:**

```bash
uv run transcribe watch ~/incoming --model small
```

---

### `transcribe-config` — управление конфигурацией

Конфиг хранится в `~/.config/audio-transcriber/config.toml`.

#### `transcribe-config set-source`

Установить папку с аудио по умолчанию.

```bash
uv run transcribe-config set-source /path/to/folder
```

#### `transcribe-config show`

Показать текущую конфигурацию.

```bash
uv run transcribe-config show
```

---

## Конфигурация

Файл: `~/.config/audio-transcriber/config.toml`

| Ключ | Тип | Описание | Умолчание |
|---|---|---|---|
| `default_source` | строка (путь) | Папка с аудио по умолчанию | — |
| `default_output` | строка (путь) | Папка для сохранения `.md` файлов | рядом с исходником |
| `default_model` | строка | Модель Whisper: `tiny`, `base`, `small`, `medium`, `large` | `base` |
| `after_transcription` | строка | Что делать с файлом после: `keep`, `delete`, `move` | `keep` |
| `processed_folder` | строка (путь) | Куда перемещать файлы при `after_transcription = "move"` | — |
| `monitor_interval` | число | Интервал проверки папки в секундах (`watch`) | `10` |
| `log_path` | строка (путь) | Путь к файлу лога | `~/.config/audio-transcriber/transcriber.log` |
| `log_max_bytes` | число | Максимальный размер лога в байтах (ротация по размеру) | `10485760` (10 МБ) |

**Пример:**

```toml
default_source = "/home/user/recordings"
default_output = "/home/user/transcripts"
default_model = "small"
after_transcription = "move"
processed_folder = "/home/user/recordings/done"
monitor_interval = 30
log_path = "/home/user/logs/transcriber.log"
log_max_bytes = 5242880
```

---

## Логирование

События записываются в лог-файл в формате plain text, одна запись на строку:

```
2026-03-11 14:23:00 WATCH_START pid=12345 source=/home/user/recordings
2026-03-11 14:23:15 FILE_START pid=12345 file=interview.mp3
2026-03-11 14:24:32 FILE_DONE pid=12345 file=interview.mp3 audio=00:45:12 started=2026-03-11 14:23:15 finished=2026-03-11 14:24:32 output=/transcripts/[2026-03-11 interview].md
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
