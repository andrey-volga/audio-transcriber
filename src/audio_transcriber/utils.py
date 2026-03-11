from pathlib import Path

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".mp4", ".m4a", ".ogg", ".flac"}


def is_audio_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def collect_audio_files(path: Path) -> list[Path]:
    """Возвращает список аудио-файлов: один файл или все файлы в директории."""
    if path.is_file():
        if not is_audio_file(path):
            raise ValueError(
                f"Неподдерживаемый формат файла: '{path.suffix}'. "
                f"Поддерживаются: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )
        return [path]

    if path.is_dir():
        files = sorted(f for f in path.iterdir() if f.is_file() and is_audio_file(f))
        if not files:
            raise ValueError(f"В директории '{path}' не найдено аудио-файлов.")
        return files

    raise FileNotFoundError(f"Файл или директория не найдены: '{path}'")


def output_path(audio_path: Path, output_dir: Path | None) -> Path:
    """Путь к выходному TXT-файлу."""
    target_dir = output_dir if output_dir else audio_path.parent
    return target_dir / (audio_path.stem + ".txt")
