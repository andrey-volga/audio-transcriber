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
        return Path(data["default_source"])
    return None
