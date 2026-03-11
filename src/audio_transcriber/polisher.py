import os
from importlib.resources import files
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

_ENV_PATH = Path.home() / ".config" / "audio-transcriber" / ".env"

SYSTEM_PROMPT = (
    files("audio_transcriber")
    .joinpath("prompts/polish_prompt.md")
    .read_text(encoding="utf-8")
    .strip()
)

ERROR_PREFIX = "⚠️ Текст не обработан — ошибка доступа к модели очистки.\n\n"


def polish_text(raw_text: str, model: str = "deepseek-chat") -> str:
    load_dotenv(_ENV_PATH)
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return ERROR_PREFIX + raw_text
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_text},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return ERROR_PREFIX + raw_text
