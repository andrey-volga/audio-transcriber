import pytest
from pathlib import Path

from audio_transcriber.utils import (
    collect_audio_files,
    handle_processed_file,
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


def test_output_path_date_format(tmp_path):
    audio = tmp_path / "interview.mp3"
    audio.touch()
    result = output_path(audio, None)
    # Name must match [YYYY-MM-DD interview].md
    assert result.suffix == ".md"
    assert result.stem.startswith("[")
    assert result.stem.endswith(" interview]")
    import re
    assert re.match(r"\[\d{4}-\d{2}-\d{2} interview\]", result.stem)
    assert result.parent == tmp_path


def test_output_path_custom_dir(tmp_path):
    audio = tmp_path / "clip.wav"
    audio.touch()
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    result = output_path(audio, out_dir)
    assert result.parent == out_dir
    assert result.suffix == ".md"
    assert "clip" in result.stem


def test_output_path_collision_suffix(tmp_path):
    audio = tmp_path / "note.mp3"
    audio.touch()

    # First call — no collision
    first = output_path(audio, None)
    assert "(2)" not in first.name
    first.touch()  # simulate existing file

    # Second call — collision, should get (2)
    second = output_path(audio, None)
    assert "(2)" in second.name
    second.touch()

    # Third call — should get (3)
    third = output_path(audio, None)
    assert "(3)" in third.name


def test_handle_processed_file_keep(tmp_path):
    audio = tmp_path / "audio.mp3"
    audio.touch()
    handle_processed_file(audio, "keep", None)
    assert audio.exists()


def test_handle_processed_file_delete(tmp_path):
    audio = tmp_path / "audio.mp3"
    audio.touch()
    handle_processed_file(audio, "delete", None)
    assert not audio.exists()


def test_handle_processed_file_move(tmp_path):
    audio = tmp_path / "audio.mp3"
    audio.touch()
    done_dir = tmp_path / "Done"
    handle_processed_file(audio, "move", done_dir)
    assert not audio.exists()
    assert (done_dir / "audio.mp3").exists()


def test_handle_processed_file_move_creates_dir(tmp_path):
    audio = tmp_path / "audio.mp3"
    audio.touch()
    done_dir = tmp_path / "nested" / "Done"
    handle_processed_file(audio, "move", done_dir)
    assert (done_dir / "audio.mp3").exists()


def test_handle_processed_file_move_without_folder(tmp_path):
    """move without processed_folder configured → file stays."""
    audio = tmp_path / "audio.mp3"
    audio.touch()
    handle_processed_file(audio, "move", None)
    assert audio.exists()
