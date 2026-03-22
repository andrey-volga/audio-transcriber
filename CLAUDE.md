# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run a single test
uv run pytest tests/test_cli.py::test_name

# Run the CLI
uv run transcribe [SOURCE] [--output DIR] [--model tiny|base|small|medium|large] [--lang LANG]
uv run transcribe watch [SOURCE] [--model MODEL] [--lang LANG]
uv run transcribe polish [SOURCE] [--output PATH]
uv run transcribe-config set-source|set-output|set-polish-output|show
```

## Architecture

Python CLI tool for offline audio/video transcription using Whisper. Python 3.13, managed with `uv`.

**Layers:**
- `cli.py` — Typer CLI entry point. Commands: `main` (transcribe files), `watch` (monitor folder), `polish` (DeepSeek cleanup), config commands. Rich progress display, logging, threading for Ctrl+C support.
- `transcriber.py` — Wraps `faster-whisper`. CPU-only, int8 quantization. Module-level `_model_cache` dict avoids reloading models between files.
- `utils.py` — Audio file detection (MP3, WAV, MP4, M4A, OGG, FLAC), directory scanning, output path generation, post-transcription file handling (keep/delete/move).
- `storage.py` — SQLite job store at `~/.config/audio-transcriber/jobs.db`. Tracks processed files by SHA-256 hash (first 64KB). Used by `watch` for persistence across restarts and deduplication by content (not filename). On startup `init_db()` resets stuck `processing` jobs to `error` for crash recovery.
- `polisher.py` — DeepSeek API integration via OpenAI-compatible client. Reads API key from `~/.config/audio-transcriber/.env`. Returns `ERROR_PREFIX + raw_text` on failure so output is never lost.
- `config.py` — TOML config at `~/.config/audio-transcriber/config.toml`. Keys: `default_source`, `default_output`, `polish_output`, `raw_done_folder`, `deepseek_model`, `default_model`, `after_transcription`, `processed_folder`, `monitor_interval`, `log_path`, `log_max_bytes`. When generating or editing the config file always include all available keys with inline comments explaining each option.

**Key behaviors:**
- Default language is Russian (`ru`); configurable via `--lang`.
- Output format is `.md` (named `[YYYY-MM-DD stem].md` from file mtime). Auto-suffixes `(2)`, `(3)` on collision.
- Batch mode continues on individual file failures.
- `watch` is persistent: uses SQLite to skip already-processed files across restarts. Error jobs are retried on next scan.
- After transcription, `after_transcription` config determines what happens to the source audio: `keep` (default), `delete`, or `move` to `processed_folder`.
- Requires `ffmpeg` as a system dependency (not in pyproject.toml).

**Tests** mock `transcriber.transcribe` and `polisher.polish_text` to avoid model inference. The `isolated_db` fixture redirects `storage.DB_PATH` to `tmp_path` so watch tests don't share state.
