from pathlib import Path

import pytest
from typer.testing import CliRunner

from audio_transcriber.cli import app

runner = CliRunner()


@pytest.fixture
def audio_file(tmp_path):
    f = tmp_path / "sample.mp3"
    f.touch()
    return f


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "транскрибац" in result.output.lower() or "transcrib" in result.output.lower()


def test_unsupported_format(tmp_path):
    f = tmp_path / "doc.pdf"
    f.touch()
    result = runner.invoke(app, [str(f)])
    assert result.exit_code == 1


def test_nonexistent_file(tmp_path):
    result = runner.invoke(app, [str(tmp_path / "ghost.mp3")])
    assert result.exit_code != 0


def test_transcribe_single_file(tmp_path, audio_file, mocker):
    mocker.patch(
        "audio_transcriber.cli.transcribe",
        return_value="Привет, это тестовая транскрипция.",
    )
    result = runner.invoke(app, [str(audio_file), "--output", str(tmp_path)])
    assert result.exit_code == 0
    out_file = tmp_path / "sample.txt"
    assert out_file.exists()
    assert out_file.read_text(encoding="utf-8") == "Привет, это тестовая транскрипция."


def test_transcribe_directory(tmp_path, mocker):
    (tmp_path / "a.mp3").touch()
    (tmp_path / "b.wav").touch()
    out_dir = tmp_path / "out"
    mocker.patch("audio_transcriber.cli.transcribe", return_value="текст")
    result = runner.invoke(app, [str(tmp_path), "--output", str(out_dir)])
    assert result.exit_code == 0
    assert (out_dir / "a.txt").read_text() == "текст"
    assert (out_dir / "b.txt").read_text() == "текст"


def test_transcribe_error_continues(tmp_path, mocker):
    (tmp_path / "good.mp3").touch()
    (tmp_path / "bad.wav").touch()
    out_dir = tmp_path / "out"

    def side_effect(path, **kwargs):
        if path.name == "bad.wav":
            raise RuntimeError("сломалось")
        return "хороший текст"

    mocker.patch("audio_transcriber.cli.transcribe", side_effect=side_effect)
    result = runner.invoke(app, [str(tmp_path), "--output", str(out_dir)])
    assert result.exit_code == 1  # есть ошибка
    assert (out_dir / "good.txt").read_text() == "хороший текст"  # но хороший файл создан
