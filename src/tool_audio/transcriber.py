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
) -> tuple[str, float]:
    """
    Транскрибирует аудио-файл и возвращает текст и длительность.

    Args:
        audio_path: путь к аудио/видео-файлу.
        model_name: размер модели Whisper (tiny, base, small, medium, large-v3).
        language: код языка транскрибации (ru, en, ...).

    Returns:
        Кортеж (текст транскрипции, длительность аудио в секундах).
        Длительность берётся из конца последнего сегмента (0.0 если сегментов нет).
    """
    model = _load_model(model_name)
    segments, _ = model.transcribe(str(audio_path), language=language)
    parts = []
    duration = 0.0
    for segment in segments:
        parts.append(segment.text.strip())
        duration = segment.end
    return " ".join(parts).strip(), duration
