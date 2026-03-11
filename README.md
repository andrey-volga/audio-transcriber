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

| Ключ | Тип | Описание |
|---|---|---|
| `default_source` | строка (путь) | Папка с аудио по умолчанию |
| `default_output` | строка (путь) | Папка для сохранения `.md` по умолчанию |
| `default_model` | строка | Модель Whisper по умолчанию (`base`, `small`, ...) |
| `after_transcription` | строка | Что делать с файлом после: `keep`, `delete`, `move` |
| `processed_folder` | строка (путь) | Куда перемещать файлы при `after_transcription = "move"` |
| `monitor_interval` | число | Интервал проверки папки в секундах (по умолчанию `10`) |

**Пример:**

```toml
default_source = "/home/user/recordings"
default_output = "/home/user/transcripts"
default_model = "small"
after_transcription = "move"
processed_folder = "/home/user/recordings/done"
monitor_interval = 30
```

---

## Поддерживаемые форматы

`MP3`, `WAV`, `MP4`, `M4A`, `OGG`, `FLAC`
