import tomllib
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "audio-transcriber" / "config.toml"


def load() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("rb") as f:
        return tomllib.load(f)


def save(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, value in data.items():
        if isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        else:
            lines.append(f"{key} = {value}")
    CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def get_default_source() -> Path | None:
    data = load()
    if "default_source" in data:
        return Path(data["default_source"]).expanduser()
    return None


def get_default_model() -> str | None:
    data = load()
    return data.get("default_model")


def get_default_output() -> Path | None:
    data = load()
    if "default_output" in data:
        return Path(data["default_output"]).expanduser()
    return None


def get_after_transcription() -> str:
    data = load()
    return data.get("after_transcription", "keep")


def get_processed_folder() -> Path | None:
    data = load()
    if "processed_folder" in data:
        return Path(data["processed_folder"]).expanduser()
    return None


def get_monitor_interval() -> int:
    data = load()
    return int(data.get("monitor_interval", 10))


def get_log_path() -> Path:
    data = load()
    if "log_path" in data:
        return Path(data["log_path"]).expanduser()
    return CONFIG_PATH.parent / "transcriber.log"


def get_log_max_bytes() -> int:
    data = load()
    return int(data.get("log_max_bytes", 10 * 1024 * 1024))


_POLISH_OUTPUT_DEFAULT = "~/Obsidian/00. Inbox/Transcribes"


def get_polish_output() -> Path:
    data = load()
    if "polish_output" not in data:
        data["polish_output"] = _POLISH_OUTPUT_DEFAULT
        save(data)
    return Path(data["polish_output"]).expanduser()


def get_deepseek_model() -> str:
    data = load()
    return data.get("deepseek_model", "deepseek-chat")


def get_polish_provider() -> str:
    data = load()
    return data.get("polish_provider", "deepseek")


def get_groq_model() -> str:
    data = load()
    return data.get("groq_model", "llama-3.3-70b-versatile")


def get_raw_done_folder() -> Path | None:
    data = load()
    if "raw_done_folder" in data:
        return Path(data["raw_done_folder"]).expanduser()
    return None
