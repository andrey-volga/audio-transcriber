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
uv run transcribe <source> [--output DIR] [--model tiny|base|small|medium|large] [--lang LANG]
```

## Architecture

This is a Python CLI tool for offline audio/video transcription using Whisper. Python 3.13, managed with `uv`.

**Layers:**
- `cli.py` — Typer CLI entry point. Handles single files and batch directories, Rich progress display, validation.
- `transcriber.py` — Wraps `faster-whisper`. Runs on CPU with int8 quantization. Caches loaded models in a module-level `_model_cache` dict to avoid reloading.
- `utils.py` — Audio file detection (MP3, WAV, MP4, M4A, OGG, FLAC), directory scanning, output path generation (`.txt` alongside source).

**Key behaviors:**
- Default language is Russian (`ru`); configurable via `--lang`.
- Batch mode continues on individual file failures.
- Output is plain UTF-8 text with no timestamps.
- Requires `ffmpeg` as a system dependency (not in pyproject.toml).

Tests mock the transcription engine (`transcriber.transcribe`) to avoid actual model inference.
