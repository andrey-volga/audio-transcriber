import pytest
from pathlib import Path

from audio_transcriber.utils import (
    collect_audio_files,
    is_audio_file,
    output_path,
    SUPPORTED_EXTENSIONS,
)


def test_is_audio_file_supported():
    for ext in SUPPORTED_EXTENSIONS:
        assert is_audio_file(Path(f"file{ext}"))


def test_is_audio_file_unsupported():
    assert not is_audio_file(Path("file.pdf"))
    assert not is_audio_file(Path("file.txt"))


def test_collect_single_file(tmp_path):
    f = tmp_path / "audio.mp3"
    f.touch()
    assert collect_audio_files(f) == [f]


def test_collect_single_file_wrong_format(tmp_path):
    f = tmp_path / "doc.pdf"
    f.touch()
    with pytest.raises(ValueError, match="Неподдерживаемый формат"):
        collect_audio_files(f)


def test_collect_directory(tmp_path):
    (tmp_path / "a.mp3").touch()
    (tmp_path / "b.wav").touch()
    (tmp_path / "ignore.txt").touch()
    result = collect_audio_files(tmp_path)
    assert len(result) == 2
    assert all(is_audio_file(f) for f in result)


def test_collect_empty_directory(tmp_path):
    with pytest.raises(ValueError, match="не найдено аудио-файлов"):
        collect_audio_files(tmp_path)


def test_collect_nonexistent_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        collect_audio_files(tmp_path / "ghost.mp3")


def test_output_path_same_dir():
    p = Path("/data/recordings/interview.mp3")
    assert output_path(p, None) == Path("/data/recordings/interview.txt")


def test_output_path_custom_dir(tmp_path):
    p = Path("/data/audio.wav")
    result = output_path(p, tmp_path)
    assert result == tmp_path / "audio.txt"
