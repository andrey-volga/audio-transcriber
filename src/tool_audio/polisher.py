import os
from importlib.resources import files
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

_ENV_PATH = Path.home() / ".config" / "tool-audio" / ".env"

SYSTEM_PROMPT = (
    files("tool_audio")
    .joinpath("prompts/polish_prompt.md")
    .read_text(encoding="utf-8")
    .strip()
)

ERROR_PREFIX = "⚠️ Текст не обработан — ошибка доступа к модели очистки.\n\n"

_PROVIDERS = {
    "deepseek": {
        "env_key": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
        "max_tokens": 8192,
    },
    "groq": {
        "env_key": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "max_tokens": 32768,
    },
}


def polish_text(raw_text: str, model: str = "deepseek-chat", provider: str = "deepseek") -> str:
    cfg = _PROVIDERS.get(provider, _PROVIDERS["deepseek"])
    load_dotenv(_ENV_PATH)
    api_key = os.getenv(cfg["env_key"])
    if not api_key:
        return ERROR_PREFIX + raw_text
    try:
        client = OpenAI(api_key=api_key, base_url=cfg["base_url"])
        response = client.chat.completions.create(
            model=model,
            max_tokens=cfg["max_tokens"],
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_text},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return ERROR_PREFIX + raw_text
