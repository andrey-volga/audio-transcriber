from pathlib import Path

from faster_whisper import WhisperModel


_model_cache: dict[str, WhisperModel] = {}


def _load_model(model_name: str) -> WhisperModel:
    if model_name not in _model_cache:
        _model_cache[model_name] = WhisperModel(model_name, device="cpu", compute_type="int8")
    return _model_cache[model_name]


def transcribe(
    audio_path: Path,
    model_name: str = "base",
    language: str = "ru",
) -> str:
    """
    Транскрибирует аудио-файл и возвращает текст.

    Args:
        audio_path: путь к аудио/видео-файлу.
        model_name: размер модели Whisper (tiny, base, small, medium, large-v3).
        language: код языка транскрибации (ru, en, ...).

    Returns:
        Строка с транскрипцией.
    """
    model = _load_model(model_name)
    segments, _ = model.transcribe(str(audio_path), language=language)
    return " ".join(segment.text.strip() for segment in segments).strip()
