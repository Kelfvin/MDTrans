from __future__ import annotations

import tiktoken


ENCODING_NAME = "cl100k_base"


def get_encoding():
    try:
        return tiktoken.get_encoding(ENCODING_NAME)
    except Exception as exc:
        raise RuntimeError(
            "Failed to initialize the OpenAI tokenizer 'cl100k_base'. "
            "The tokenizer resource may need to be downloaded first, and your current network/proxy setup may be blocking it."
        ) from exc


def count_tokens(text: str) -> int:
    return len(get_encoding().encode(text))
