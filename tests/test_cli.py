from pathlib import Path

import pytest
from typer.testing import CliRunner

import audio_transcriber.storage as storage_mod
from audio_transcriber.cli import app, _fmt_duration

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Redirect SQLite DB to tmp_path so watch tests don't share state."""
    monkeypatch.setattr(storage_mod, "DB_PATH", tmp_path / "test_jobs.db")


@pytest.fixture
def audio_file(tmp_path):
    f = tmp_path / "sample.mp3"
    f.touch()
    return f


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "main" in result.output or "watch" in result.output


def test_unsupported_format(tmp_path):
    f = tmp_path / "doc.pdf"
    f.touch()
    result = runner.invoke(app, ["main", str(f)])
    assert result.exit_code == 1


def test_nonexistent_file(tmp_path):
    result = runner.invoke(app, ["main", str(tmp_path / "ghost.mp3")])
    assert result.exit_code != 0


def test_transcribe_single_file(tmp_path, audio_file, mocker):
    mocker.patch("audio_transcriber.cli.transcribe", return_value=("Привет, это тестовая транскрипция.", 42.0))
    mocker.patch("audio_transcriber.cli.handle_processed_file")
    mocker.patch("audio_transcriber.cli._setup_logger")
    mocker.patch("audio_transcriber.cli.cfg.get_polish_output", return_value=tmp_path / "polish")
    mocker.patch("audio_transcriber.cli.polish_text", return_value="Привет, это тестовая транскрипция.")
    result = runner.invoke(app, ["main", str(audio_file), "--output", str(tmp_path)])
    assert result.exit_code == 0, result.output
    # Output file is named [YYYY-MM-DD sample].md
    txt_files = list(tmp_path.glob("*.md"))
    assert len(txt_files) == 1
    assert "sample" in txt_files[0].stem
    assert txt_files[0].read_text(encoding="utf-8") == "Привет, это тестовая транскрипция."


def test_transcribe_directory(tmp_path, mocker):
    (tmp_path / "a.mp3").touch()
    (tmp_path / "b.wav").touch()
    out_dir = tmp_path / "out"
    mocker.patch("audio_transcriber.cli.transcribe", return_value=("текст", 0.0))
    mocker.patch("audio_transcriber.cli.handle_processed_file")
    mocker.patch("audio_transcriber.cli._setup_logger")
    mocker.patch("audio_transcriber.cli.cfg.get_polish_output", return_value=tmp_path / "polish")
    mocker.patch("audio_transcriber.cli.polish_text", return_value="текст")
    result = runner.invoke(app, ["main", str(tmp_path), "--output", str(out_dir)])
    assert result.exit_code == 0, result.output
    txt_files = list(out_dir.glob("*.md"))
    assert len(txt_files) == 2
    assert all(f.read_text() == "текст" for f in txt_files)


def test_transcribe_error_continues(tmp_path, mocker):
    (tmp_path / "good.mp3").touch()
    (tmp_path / "bad.wav").touch()
    out_dir = tmp_path / "out"

    def side_effect(path, **kwargs):
        if path.name == "bad.wav":
            raise RuntimeError("сломалось")
        return ("хороший текст", 10.0)

    mocker.patch("audio_transcriber.cli.transcribe", side_effect=side_effect)
    mocker.patch("audio_transcriber.cli.handle_processed_file")
    mocker.patch("audio_transcriber.cli._setup_logger")
    mocker.patch("audio_transcriber.cli.cfg.get_polish_output", return_value=tmp_path / "polish")
    mocker.patch("audio_transcriber.cli.polish_text", return_value="хороший текст")
    result = runner.invoke(app, ["main", str(tmp_path), "--output", str(out_dir)])
    assert result.exit_code == 1  # есть ошибка
    txt_files = list(out_dir.glob("*.md"))
    assert len(txt_files) == 1
    assert txt_files[0].read_text() == "хороший текст"


def test_polish_success(tmp_path, audio_file, mocker):
    raw_dir = tmp_path / "raw"
    polish_dir = tmp_path / "polish"
    mocker.patch("audio_transcriber.cli.transcribe", return_value=("сырой текст", 5.0))
    mocker.patch("audio_transcriber.cli.handle_processed_file")
    mocker.patch("audio_transcriber.cli._setup_logger")
    mocker.patch("audio_transcriber.cli.cfg.get_polish_output", return_value=polish_dir)
    mocker.patch("audio_transcriber.cli.cfg.get_deepseek_model", return_value="deepseek-chat")
    mocker.patch("audio_transcriber.cli.polish_text", return_value="чистый текст")

    result = runner.invoke(app, ["main", str(audio_file), "--output", str(raw_dir)])
    assert result.exit_code == 0, result.output
    assert "✦" in result.output
    polish_files = list(polish_dir.glob("*.md"))
    assert len(polish_files) == 1
    assert polish_files[0].read_text(encoding="utf-8") == "чистый текст"


def test_polish_api_error(tmp_path, audio_file, mocker):
    from audio_transcriber.polisher import ERROR_PREFIX
    raw_dir = tmp_path / "raw"
    polish_dir = tmp_path / "polish"
    mocker.patch("audio_transcriber.cli.transcribe", return_value=("сырой текст", 5.0))
    mocker.patch("audio_transcriber.cli.handle_processed_file")
    mocker.patch("audio_transcriber.cli._setup_logger")
    mocker.patch("audio_transcriber.cli.cfg.get_polish_output", return_value=polish_dir)
    mocker.patch("audio_transcriber.cli.cfg.get_deepseek_model", return_value="deepseek-chat")
    mocker.patch("audio_transcriber.cli.polish_text", return_value=ERROR_PREFIX + "сырой текст")

    result = runner.invoke(app, ["main", str(audio_file), "--output", str(raw_dir)])
    assert result.exit_code == 0, result.output
    assert "⚠" in result.output
    polish_files = list(polish_dir.glob("*.md"))
    assert len(polish_files) == 1
    assert polish_files[0].read_text(encoding="utf-8").startswith(ERROR_PREFIX)


def test_polish_success_moves_raw(tmp_path, audio_file, mocker):
    """После успешной полировки raw-файл перемещается в raw_done_folder."""
    raw_dir = tmp_path / "raw"
    raw_done_dir = tmp_path / "raw" / "Done"
    polish_dir = tmp_path / "polish"
    mocker.patch("audio_transcriber.cli.transcribe", return_value=("сырой текст", 5.0))
    mocker.patch("audio_transcriber.cli._setup_logger")
    mocker.patch("audio_transcriber.cli.cfg.get_polish_output", return_value=polish_dir)
    mocker.patch("audio_transcriber.cli.cfg.get_deepseek_model", return_value="deepseek-chat")
    mocker.patch("audio_transcriber.cli.cfg.get_raw_done_folder", return_value=raw_done_dir)
    mocker.patch("audio_transcriber.cli.cfg.get_after_transcription", return_value="keep")
    mocker.patch("audio_transcriber.cli.cfg.get_processed_folder", return_value=None)
    mocker.patch("audio_transcriber.cli.polish_text", return_value="чистый текст")

    result = runner.invoke(app, ["main", str(audio_file), "--output", str(raw_dir)])
    assert result.exit_code == 0, result.output

    raw_files = list(raw_dir.glob("*.md"))
    done_files = list(raw_done_dir.glob("*.md"))
    assert len(raw_files) == 0, "raw файл должен быть перемещён из raw/"
    assert len(done_files) == 1, "raw файл должен оказаться в raw/Done/"


def test_polish_error_keeps_raw(tmp_path, audio_file, mocker):
    """При ошибке API raw-файл остаётся в raw/, не перемещается."""
    from audio_transcriber.polisher import ERROR_PREFIX
    raw_dir = tmp_path / "raw"
    raw_done_dir = tmp_path / "raw" / "Done"
    polish_dir = tmp_path / "polish"
    mocker.patch("audio_transcriber.cli.transcribe", return_value=("сырой текст", 5.0))
    mocker.patch("audio_transcriber.cli._setup_logger")
    mocker.patch("audio_transcriber.cli.cfg.get_polish_output", return_value=polish_dir)
    mocker.patch("audio_transcriber.cli.cfg.get_deepseek_model", return_value="deepseek-chat")
    mocker.patch("audio_transcriber.cli.cfg.get_raw_done_folder", return_value=raw_done_dir)
    mocker.patch("audio_transcriber.cli.cfg.get_after_transcription", return_value="keep")
    mocker.patch("audio_transcriber.cli.cfg.get_processed_folder", return_value=None)
    mocker.patch("audio_transcriber.cli.polish_text", return_value=ERROR_PREFIX + "сырой текст")

    result = runner.invoke(app, ["main", str(audio_file), "--output", str(raw_dir)])
    assert result.exit_code == 0, result.output

    raw_files = list(raw_dir.glob("*.md"))
    assert len(raw_files) == 1, "raw файл должен остаться в raw/ при ошибке API"
    assert not raw_done_dir.exists(), "raw/Done/ не должна создаваться при ошибке"


# --- _fmt_duration ---

def test_fmt_duration_zero():
    assert _fmt_duration(0) == "00:00:00"


def test_fmt_duration_seconds_only():
    assert _fmt_duration(65) == "00:01:05"


def test_fmt_duration_hours():
    assert _fmt_duration(3661) == "01:01:01"


def test_fmt_duration_large():
    assert _fmt_duration(3600 * 10) == "10:00:00"


# --- watch ---

def test_watch_transcribes_new_file(tmp_path, mocker):
    (tmp_path / "a.mp3").write_bytes(b"audio content")
    out_dir = tmp_path / "out"
    mocker.patch("audio_transcriber.cli.transcribe", return_value=("текст", 30.0))
    mocker.patch("audio_transcriber.cli.handle_processed_file")
    mocker.patch("audio_transcriber.cli._setup_logger")
    mocker.patch("audio_transcriber.cli.cfg.get_default_output", return_value=out_dir)
    mocker.patch("audio_transcriber.cli.cfg.get_polish_output", return_value=tmp_path / "polish")
    mocker.patch("audio_transcriber.cli.polish_text", return_value="текст")
    mocker.patch("time.sleep", side_effect=KeyboardInterrupt)

    result = runner.invoke(app, ["watch", str(tmp_path)])
    assert result.exit_code == 0
    md_files = list(out_dir.glob("*.md"))
    assert len(md_files) == 1
    assert md_files[0].read_text() == "текст"


def test_watch_output_shows_duration(tmp_path, mocker):
    (tmp_path / "a.mp3").write_bytes(b"audio content")
    mocker.patch("audio_transcriber.cli.transcribe", return_value=("текст", 3661.0))
    mocker.patch("audio_transcriber.cli.handle_processed_file")
    mocker.patch("audio_transcriber.cli._setup_logger")
    mocker.patch("audio_transcriber.cli.cfg.get_default_output", return_value=None)
    mocker.patch("audio_transcriber.cli.cfg.get_polish_output", return_value=tmp_path / "polish")
    mocker.patch("audio_transcriber.cli.polish_text", return_value="текст")
    mocker.patch("time.sleep", side_effect=KeyboardInterrupt)

    result = runner.invoke(app, ["watch", str(tmp_path)])
    assert "01:01:01" in result.output


def test_watch_skips_already_processed_file(tmp_path, mocker):
    """Файл с тем же хэшем не обрабатывается повторно (action=keep)."""
    (tmp_path / "a.mp3").write_bytes(b"audio content")
    transcribe_mock = mocker.patch("audio_transcriber.cli.transcribe", return_value=("текст", 10.0))
    mocker.patch("audio_transcriber.cli.handle_processed_file")
    mocker.patch("audio_transcriber.cli._setup_logger")
    mocker.patch("audio_transcriber.cli.cfg.get_default_output", return_value=None)
    mocker.patch("audio_transcriber.cli.cfg.get_polish_output", return_value=tmp_path / "polish")
    mocker.patch("audio_transcriber.cli.polish_text", return_value="текст")
    mocker.patch("audio_transcriber.cli.cfg.get_after_transcription", return_value="keep")

    call_count = 0

    def sleep_side_effect(n):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise KeyboardInterrupt

    mocker.patch("time.sleep", side_effect=sleep_side_effect)

    runner.invoke(app, ["watch", str(tmp_path)])
    assert transcribe_mock.call_count == 1


def test_watch_processes_new_file_with_same_name(tmp_path, mocker):
    """Новый файл с тем же именем, но другим содержимым (другой хэш) обрабатывается заново."""
    f = tmp_path / "a.mp3"
    f.write_bytes(b"first recording")
    transcribe_mock = mocker.patch("audio_transcriber.cli.transcribe", return_value=("текст", 10.0))
    mocker.patch("audio_transcriber.cli.handle_processed_file")
    mocker.patch("audio_transcriber.cli._setup_logger")
    mocker.patch("audio_transcriber.cli.cfg.get_default_output", return_value=None)
    mocker.patch("audio_transcriber.cli.cfg.get_polish_output", return_value=tmp_path / "polish")
    mocker.patch("audio_transcriber.cli.polish_text", return_value="текст")

    call_count = 0

    def sleep_side_effect(n):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Simulate: original moved away, new file with same name but different content
            f.write_bytes(b"second recording - different content")
        elif call_count >= 2:
            raise KeyboardInterrupt

    mocker.patch("time.sleep", side_effect=sleep_side_effect)

    runner.invoke(app, ["watch", str(tmp_path)])
    assert transcribe_mock.call_count == 2


def test_watch_crash_recovery(tmp_path, mocker):
    """Файл, застрявший в processing (краш предыдущего процесса), обрабатывается повторно."""
    f = tmp_path / "a.mp3"
    f.write_bytes(b"audio content")

    # Simulate a previous crashed run: insert file as 'processing'
    storage_mod.init_db()
    h = storage_mod.file_hash(f)
    storage_mod.add_job(f, h)
    assert storage_mod.is_processed(h)  # stuck in processing

    transcribe_mock = mocker.patch("audio_transcriber.cli.transcribe", return_value=("текст", 10.0))
    mocker.patch("audio_transcriber.cli.handle_processed_file")
    mocker.patch("audio_transcriber.cli._setup_logger")
    mocker.patch("audio_transcriber.cli.cfg.get_default_output", return_value=None)
    mocker.patch("audio_transcriber.cli.cfg.get_polish_output", return_value=tmp_path / "polish")
    mocker.patch("audio_transcriber.cli.polish_text", return_value="текст")
    mocker.patch("audio_transcriber.cli.cfg.get_after_transcription", return_value="keep")
    mocker.patch("time.sleep", side_effect=KeyboardInterrupt)

    # watch calls init_db() on startup — should reset 'processing' → 'error', then re-process
    runner.invoke(app, ["watch", str(tmp_path)])
    assert transcribe_mock.call_count == 1


def test_watch_continues_on_error(tmp_path, mocker):
    """Ошибка транскрибации одного файла не останавливает watch."""
    (tmp_path / "bad.mp3").write_bytes(b"bad audio")
    (tmp_path / "good.wav").write_bytes(b"good audio")

    def side_effect(path, **kwargs):
        if path.name == "bad.mp3":
            raise RuntimeError("сломалось")
        return ("текст", 5.0)

    mocker.patch("audio_transcriber.cli.transcribe", side_effect=side_effect)
    mocker.patch("audio_transcriber.cli.handle_processed_file")
    mocker.patch("audio_transcriber.cli._setup_logger")
    mocker.patch("audio_transcriber.cli.cfg.get_default_output", return_value=None)
    mocker.patch("audio_transcriber.cli.cfg.get_polish_output", return_value=tmp_path / "polish")
    mocker.patch("audio_transcriber.cli.polish_text", return_value="текст")
    mocker.patch("time.sleep", side_effect=KeyboardInterrupt)

    result = runner.invoke(app, ["watch", str(tmp_path)])
    assert result.exit_code == 0
    assert "сломалось" in result.output
