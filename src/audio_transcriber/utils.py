from datetime import datetime
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
    """Путь к выходному MD-файлу. Имя: [YYYY-MM-DD stem].md, с суффиксом при коллизии."""
    target_dir = output_dir if output_dir else audio_path.parent
    mtime = datetime.fromtimestamp(audio_path.stat().st_mtime)
    date_str = mtime.strftime("%Y-%m-%d")
    base = f"[{date_str} {audio_path.stem}]"
    candidate = target_dir / f"{base}.md"
    counter = 2
    while candidate.exists():
        candidate = target_dir / f"{base} ({counter}).md"
        counter += 1
    return candidate


def handle_processed_file(audio_path: Path, action: str, processed_folder: Path | None) -> None:
    """Обработать аудио-файл после транскрибации: keep / delete / move."""
    if action == "delete":
        audio_path.unlink()
    elif action == "move" and processed_folder:
        processed_folder.mkdir(parents=True, exist_ok=True)
        audio_path.rename(processed_folder / audio_path.name)
