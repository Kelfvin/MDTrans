from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from mdtrans.constants import CONFIG_PATH


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    model: str
    context_window: int


def read_llm_config(config_path: Path = Path(CONFIG_PATH)) -> LLMConfig:
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")

    with config_path.open("rb") as handle:
        data = tomllib.load(handle)

    llm_data = data.get("llm")
    if not isinstance(llm_data, dict):
        raise ValueError(f"Missing [llm] section in {config_path}")

    base_url = llm_data.get("base_url")
    model = llm_data.get("model")
    context_window = llm_data.get("context_window")

    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError(f"Missing non-empty llm.base_url in {config_path}")
    if not isinstance(model, str) or not model.strip():
        raise ValueError(f"Missing non-empty llm.model in {config_path}")
    if not isinstance(context_window, int) or context_window <= 0:
        raise ValueError(f"Missing positive integer llm.context_window in {config_path}")

    return LLMConfig(
        base_url=base_url.strip(),
        model=model.strip(),
        context_window=context_window,
    )


def require_openai_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is required but not set.")
    return api_key
