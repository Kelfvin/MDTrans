from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from mdtrans.constants import CONFIG_PATH

DEFAULT_CONFIG_TEMPLATE = """[llm]
base_url = "https://api.deepseek.com"
model = "deepseek-chat"
context_window = 64000
max_output_tokens = 8000
max_chunk_tokens = 5000
"""


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    model: str
    context_window: int
    max_output_tokens: int
    max_chunk_tokens: int


def create_default_config_template(config_path: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")


def read_llm_config(config_path: Path = Path(CONFIG_PATH)) -> LLMConfig:
    config_path = config_path.expanduser()
    if not config_path.exists():
        create_default_config_template(config_path)
        raise FileNotFoundError(
            f"Created config template at {config_path}. Please edit it and run again."
        )

    with config_path.open("rb") as handle:
        data = tomllib.load(handle)

    llm_data = data.get("llm")
    if not isinstance(llm_data, dict):
        raise ValueError(f"Missing [llm] section in {config_path}")

    base_url = llm_data.get("base_url")
    model = llm_data.get("model")
    context_window = llm_data.get("context_window")
    max_output_tokens = llm_data.get("max_output_tokens")
    max_chunk_tokens = llm_data.get("max_chunk_tokens")

    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError(f"Missing non-empty llm.base_url in {config_path}")
    if not isinstance(model, str) or not model.strip():
        raise ValueError(f"Missing non-empty llm.model in {config_path}")
    if not isinstance(context_window, int) or context_window <= 0:
        raise ValueError(f"Missing positive integer llm.context_window in {config_path}")
    if not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
        raise ValueError(f"Missing positive integer llm.max_output_tokens in {config_path}")
    if not isinstance(max_chunk_tokens, int) or max_chunk_tokens <= 0:
        raise ValueError(f"Missing positive integer llm.max_chunk_tokens in {config_path}")

    return LLMConfig(
        base_url=base_url.strip(),
        model=model.strip(),
        context_window=context_window,
        max_output_tokens=max_output_tokens,
        max_chunk_tokens=max_chunk_tokens,
    )


def require_openai_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is required but not set.")
    return api_key
