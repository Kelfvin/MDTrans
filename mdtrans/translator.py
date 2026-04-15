from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from mdtrans.chunking import TranslationChunk, split_markdown_into_chunks
from mdtrans.config import LLMConfig, require_openai_api_key
from mdtrans.constants import RESERVED_OUTPUT_TOKENS, TRANSLATION_SYSTEM_PROMPT
from mdtrans.discovery import discover_markdown_files
from mdtrans.tokenizer import count_tokens


def build_translation_model(llm_config: LLMConfig) -> ChatOpenAI:
    """
    Builds a translation model using the given LLM configuration.

    Returns:
        A callable that takes a chunk of text and returns a translated string.
    """
    api_key = require_openai_api_key()

    return ChatOpenAI(
        api_key=api_key,
        base_url=llm_config.base_url,
        model=llm_config.model,
    )


def resolve_input_token_budget(llm_config: LLMConfig) -> int:
    prompt_tokens = count_tokens(TRANSLATION_SYSTEM_PROMPT)
    token_budget = llm_config.context_window - prompt_tokens - RESERVED_OUTPUT_TOKENS
    if token_budget <= 0:
        raise ValueError(
            "llm.context_window is too small for the translation prompt and reserved output budget."
        )
    return token_budget


async def translate_chunk(llm: ChatOpenAI, chunk: str) -> str:
    """
    Translates a single chunk of text using the given language model.

    Returns:
        The translated text as a string.
    """

    response = await llm.ainvoke(
        [
            SystemMessage(content=TRANSLATION_SYSTEM_PROMPT),
            HumanMessage(content=chunk),
        ]
    )
    return (
        response.content if isinstance(response.content, str) else str(response.content)
    )


async def translate_markdown_file(
    markdown_path: Path, llm: ChatOpenAI, token_budget: int
) -> Path:
    """
    Translates a single Markdown file using the given language model.

    Returns:
        The path to the translated file.
    """
    output_path = markdown_path.with_name(f"{markdown_path.stem}.zh.md")
    source_text = markdown_path.read_text(encoding="utf-8")
    chunks = split_markdown_into_chunks(source_text, token_budget=token_budget)

    print(f"Translating Markdown: {markdown_path}")
    translated_parts: list[str] = []
    translatable_total = len(chunks)
    translatable_index = 0

    for chunk in chunks:
        translatable_index += 1
        print(
            "  translating chunk "
            f"{translatable_index}/{translatable_total} "
            f"[{chunk.reason}|{chunk.token_count} tokens|{len(chunk.text)} chars]"
        )
        translated_parts.append(await translate_chunk(llm, chunk.text))

    output_path.write_text("".join(translated_parts), encoding="utf-8")
    print(f"Translated Markdown written to {output_path}")
    return output_path


async def translate_mineru_outputs(
    pdf_path: Path, output_dir: Path, llm_config: LLMConfig
) -> list[Path]:
    """
    Translates all Markdown files in the Mineru output directory.

    Returns:
        A list of paths to the translated files.
    """
    llm = build_translation_model(llm_config)
    token_budget = resolve_input_token_budget(llm_config)
    markdown_files = discover_markdown_files(pdf_path, output_dir)
    translated_files: list[Path] = []
    for markdown_path in markdown_files:
        translated_files.append(await translate_markdown_file(markdown_path, llm, token_budget))
    return translated_files
