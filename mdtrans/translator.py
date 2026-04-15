from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from mdtrans.chunking import TranslationChunk, split_chunk_for_retry, split_markdown_into_chunks
from mdtrans.config import LLMConfig, require_openai_api_key
from mdtrans.constants import OUTPUT_TOKEN_MARGIN, TRANSLATION_SYSTEM_PROMPT
from mdtrans.discovery import discover_markdown_files
from mdtrans.tokenizer import count_tokens

MAX_RETRY_DEPTH = 12


@dataclass(frozen=True)
class TranslationResponse:
    text: str
    finish_reason: str | None


def normalize_block_math_markdown(text: str) -> str:
    if "$$" not in text:
        return text

    normalized = text
    while "$$$$" in normalized:
        normalized = normalized.replace("$$$$", "$$\n\n$$")
    normalized = re.sub(r"([^\n])\$\$\n", r"\1\n\n$$\n", normalized)
    normalized = re.sub(r"\n\$\$([^\n])", r"\n$$\n\n\1", normalized)
    normalized = re.sub(r"([^\n])\$\$([^\n])", r"\1\n\n$$\n\n\2", normalized)
    return normalized


def normalize_html_table_markdown(text: str) -> str:
    if "<table>" not in text:
        return text

    normalized = text
    normalized = re.sub(r"([^\n])<table>", r"\1\n\n<table>", normalized)
    normalized = re.sub(r"</table>([^\n])", r"</table>\n\n\1", normalized)
    return normalized


def normalize_translated_markdown(text: str) -> str:
    normalized = normalize_block_math_markdown(text)
    normalized = normalize_html_table_markdown(normalized)
    return normalized


def build_translation_model(llm_config: LLMConfig) -> ChatOpenAI:
    api_key = require_openai_api_key()
    return ChatOpenAI(
        api_key=api_key,
        base_url=llm_config.base_url,
        model=llm_config.model,
        max_tokens=llm_config.max_output_tokens,
    )


def resolve_translation_token_budget(llm_config: LLMConfig) -> int:
    prompt_tokens = count_tokens(TRANSLATION_SYSTEM_PROMPT)
    input_budget = llm_config.context_window - prompt_tokens - llm_config.max_output_tokens
    output_budget = llm_config.max_output_tokens - OUTPUT_TOKEN_MARGIN
    token_budget = min(input_budget, output_budget, llm_config.max_chunk_tokens)
    if input_budget <= 0:
        raise ValueError(
            "llm.context_window is too small for the translation prompt and max_output_tokens."
        )
    if output_budget <= 0:
        raise ValueError(
            "llm.max_output_tokens is too small for safe translation output."
        )
    if llm_config.max_chunk_tokens <= 0:
        raise ValueError("llm.max_chunk_tokens must be a positive integer.")
    return token_budget


async def translate_chunk(llm: ChatOpenAI, chunk: str) -> TranslationResponse:
    response = await llm.ainvoke(
        [
            SystemMessage(content=TRANSLATION_SYSTEM_PROMPT),
            HumanMessage(content=chunk),
        ]
    )
    finish_reason = None
    if isinstance(response.response_metadata, dict):
        finish_reason = response.response_metadata.get("finish_reason")
    translated = response.content if isinstance(response.content, str) else str(response.content)
    return TranslationResponse(
        text=normalize_translated_markdown(translated),
        finish_reason=finish_reason,
    )


async def translate_chunk_with_retry(
    llm: ChatOpenAI,
    chunk: TranslationChunk,
    token_budget: int,
    *,
    label: str,
    depth: int = 0,
) -> str:
    if depth > MAX_RETRY_DEPTH:
        raise RuntimeError(f"Exceeded retry depth while translating chunk {label}.")

    response = await translate_chunk(llm, chunk.text)
    if response.finish_reason in (None, "stop"):
        return response.text
    if response.finish_reason != "length":
        raise RuntimeError(f"Chunk {label} failed with finish_reason={response.finish_reason}.")

    print(f"  warning: model finish_reason=length on chunk {label}, splitting and retrying")
    try:
        retry_chunks = split_chunk_for_retry(chunk, token_budget)
    except ValueError as exc:
        raise RuntimeError(f"Chunk {label} could not be split further after truncation.") from exc

    translated_parts: list[str] = []
    for index, retry_chunk in enumerate(retry_chunks, start=1):
        retry_label = f"{label}.{index}"
        print(
            "  retrying chunk "
            f"{retry_label} "
            f"[{retry_chunk.reason}|{retry_chunk.token_count} tokens|{len(retry_chunk.text)} chars]"
        )
        translated_parts.append(
            await translate_chunk_with_retry(
                llm,
                retry_chunk,
                token_budget,
                label=retry_label,
                depth=depth + 1,
            )
        )
    return "".join(translated_parts)


async def translate_markdown_file(
    markdown_path: Path, llm: ChatOpenAI, token_budget: int
) -> Path:
    output_path = markdown_path.with_name(f"{markdown_path.stem}.zh.md")
    source_text = markdown_path.read_text(encoding="utf-8")
    chunks = split_markdown_into_chunks(source_text, token_budget=token_budget)

    print(f"Translating Markdown: {markdown_path}")
    translated_parts: list[str] = []
    translatable_total = len(chunks)

    for translatable_index, chunk in enumerate(chunks, start=1):
        print(
            "  translating chunk "
            f"{translatable_index}/{translatable_total} "
            f"[{chunk.reason}|{chunk.token_count} tokens|{len(chunk.text)} chars]"
        )
        translated_parts.append(
            await translate_chunk_with_retry(
                llm,
                chunk,
                token_budget,
                label=str(translatable_index),
            )
        )

    output_text = normalize_translated_markdown("".join(translated_parts))
    output_path.write_text(output_text, encoding="utf-8")
    print(f"Translated Markdown written to {output_path}")
    return output_path


async def translate_mineru_outputs(
    pdf_path: Path, output_dir: Path, llm_config: LLMConfig
) -> list[Path]:
    llm = build_translation_model(llm_config)
    token_budget = resolve_translation_token_budget(llm_config)
    markdown_files = discover_markdown_files(pdf_path, output_dir)
    translated_files: list[Path] = []
    for markdown_path in markdown_files:
        translated_files.append(await translate_markdown_file(markdown_path, llm, token_budget))
    return translated_files
