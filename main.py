from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


CONFIG_PATH = Path("config.toml")
BACKEND = "hybrid-auto-engine"
TRANSLATION_CHUNK_SIZE = 3500

ChunkType = Literal["translate", "passthrough"]

TRANSLATION_SYSTEM_PROMPT = """You translate Markdown from English to Simplified Chinese.

Rules:
- Preserve the original Markdown structure exactly.
- Translate natural language text into Simplified Chinese.
- Do not change fenced code blocks, inline code, URLs, image paths, link destinations, HTML tags, or YAML frontmatter keys.
- Keep mathematical formulas and LaTeX syntax unchanged.
- Preserve headings, lists, blockquotes, tables, and emphasis markers.
- Return Markdown only. Do not add explanations."""


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    model: str


def resolve_mineru_cli() -> str:
    venv_cli = Path(".venv/bin/mineru")
    if venv_cli.exists():
        return str(venv_cli)

    mineru_cli = shutil.which("mineru")
    if mineru_cli is None:
        raise FileNotFoundError("MinerU CLI not found. Expected `.venv/bin/mineru` or `mineru` on PATH.")
    return mineru_cli


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mdtrans",
        description="Convert a PDF with MinerU and translate the generated Markdown into Simplified Chinese.",
    )
    parser.add_argument("pdf_path", help="Path to the source PDF file.")
    parser.add_argument("output_dir", help="Directory where MinerU outputs and translated Markdown will be written.")
    return parser.parse_args(argv)


def resolve_pdf_path(pdf_path_arg: str) -> Path:
    pdf_path = Path(pdf_path_arg).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"Input PDF not found: {pdf_path}")
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Input PDF is not a file: {pdf_path}")
    return pdf_path


def resolve_output_dir(output_dir_arg: str) -> Path:
    return Path(output_dir_arg).expanduser().resolve()


def read_llm_config(config_path: Path = CONFIG_PATH) -> LLMConfig:
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")

    with config_path.open("rb") as handle:
        data = tomllib.load(handle)

    llm_data = data.get("llm")
    if not isinstance(llm_data, dict):
        raise ValueError(f"Missing [llm] section in {config_path}")

    base_url = llm_data.get("base_url")
    model = llm_data.get("model")

    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError(f"Missing non-empty llm.base_url in {config_path}")
    if not isinstance(model, str) or not model.strip():
        raise ValueError(f"Missing non-empty llm.model in {config_path}")

    return LLMConfig(base_url=base_url.strip(), model=model.strip())


def require_openai_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is required but not set.")
    return api_key


def build_translation_model(llm_config: LLMConfig):
    api_key = require_openai_api_key()

    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise ImportError("Missing translation dependency: install `langchain-openai` and `langchain`.") from exc

    return ChatOpenAI(
        api_key=api_key,
        base_url=llm_config.base_url,
        model=llm_config.model,
    )


def discover_markdown_files(pdf_path: Path, output_dir: Path) -> list[Path]:
    stem = pdf_path.stem
    candidates = sorted(
        path
        for path in output_dir.rglob("*.md")
        if path.is_file() and not path.name.endswith(".zh.md") and stem in str(path)
    )
    if candidates:
        return candidates

    fallback = sorted(
        path for path in output_dir.rglob("*.md") if path.is_file() and not path.name.endswith(".zh.md")
    )
    if not fallback:
        raise FileNotFoundError(f"No Markdown files found under {output_dir}")
    return fallback


def split_markdown_into_chunks(text: str, max_chars: int = TRANSLATION_CHUNK_SIZE) -> list[tuple[ChunkType, str]]:
    chunks: list[tuple[ChunkType, str]] = []
    current: list[str] = []
    current_len = 0
    in_code_block = False
    code_block_lines: list[str] = []

    def flush_current() -> None:
        nonlocal current, current_len
        if current:
            chunks.append(("translate", "".join(current)))
            current = []
            current_len = 0

    def push_translate_line(line: str) -> None:
        nonlocal current_len
        if current_len + len(line) > max_chars and current:
            flush_current()
        current.append(line)
        current_len += len(line)

    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if in_code_block:
                code_block_lines.append(line)
                chunks.append(("passthrough", "".join(code_block_lines)))
                code_block_lines = []
                in_code_block = False
            else:
                flush_current()
                in_code_block = True
                code_block_lines = [line]
            continue

        if in_code_block:
            code_block_lines.append(line)
            continue

        if line.startswith("---") and not current and not chunks:
            push_translate_line(line)
            continue

        if line.startswith("#"):
            flush_current()
            push_translate_line(line)
            continue

        if not line.strip():
            push_translate_line(line)
            if current_len >= max_chars * 0.8:
                flush_current()
            continue

        push_translate_line(line)

    if code_block_lines:
        chunks.append(("passthrough", "".join(code_block_lines)))
    flush_current()
    return [(kind, content) for kind, content in chunks if content]


async def translate_chunk(llm, chunk: str) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage

    response = await llm.ainvoke(
        [
            SystemMessage(content=TRANSLATION_SYSTEM_PROMPT),
            HumanMessage(content=chunk),
        ]
    )
    return response.content if isinstance(response.content, str) else str(response.content)


async def translate_markdown_file(markdown_path: Path, llm) -> Path:
    output_path = markdown_path.with_name(f"{markdown_path.stem}.zh.md")
    source_text = markdown_path.read_text(encoding="utf-8")
    chunks = split_markdown_into_chunks(source_text)

    print(f"Translating Markdown: {markdown_path}")
    translated_parts: list[str] = []
    translatable_total = sum(1 for kind, _ in chunks if kind == "translate")
    translatable_index = 0

    for kind, content in chunks:
        if kind == "passthrough":
            translated_parts.append(content)
            continue

        translatable_index += 1
        print(f"  translating chunk {translatable_index}/{translatable_total}")
        translated_parts.append(await translate_chunk(llm, content))

    output_path.write_text("".join(translated_parts), encoding="utf-8")
    print(f"Translated Markdown written to {output_path}")
    return output_path


async def stream_lines(stream: asyncio.StreamReader | None, prefix: str) -> list[str]:
    if stream is None:
        return []

    lines: list[str] = []
    while True:
        line = await stream.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="replace").rstrip()
        lines.append(text)
        print(f"[{prefix}] {text}")
    return lines


async def run_mineru(pdf_path: Path, output_dir: Path) -> None:
    cli = resolve_mineru_cli()
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        cli,
        "-p",
        str(pdf_path),
        "-o",
        str(output_dir),
        "-b",
        BACKEND,
    ]

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    print(f"Starting MinerU: {' '.join(cmd)}")
    sys.stdout.flush()

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout_task = asyncio.create_task(stream_lines(process.stdout, "stdout"))
    stderr_task = asyncio.create_task(stream_lines(process.stderr, "stderr"))
    _, stderr_lines = await asyncio.gather(stdout_task, stderr_task)
    returncode = await process.wait()
    stderr_text = "\n".join(line for line in stderr_lines if line).strip()

    if returncode != 0:
        error_message = [
            f"MinerU exited with code {returncode}.",
            f"Command: {' '.join(cmd)}",
        ]
        if stderr_text:
            error_message.append(f"stderr:\n{stderr_text}")
        raise RuntimeError("\n".join(error_message))


async def translate_mineru_outputs(pdf_path: Path, output_dir: Path, llm_config: LLMConfig) -> list[Path]:
    llm = build_translation_model(llm_config)
    markdown_files = discover_markdown_files(pdf_path, output_dir)
    translated_files: list[Path] = []
    for markdown_path in markdown_files:
        translated_files.append(await translate_markdown_file(markdown_path, llm))
    return translated_files


async def async_main(pdf_path: Path, output_dir: Path) -> None:
    llm_config = read_llm_config()
    require_openai_api_key()
    print(f"Using input PDF: {pdf_path}")
    await run_mineru(pdf_path, output_dir)
    print(f"MinerU output directory: {output_dir}")
    translated_files = await translate_mineru_outputs(pdf_path, output_dir, llm_config)
    print("Chinese Markdown outputs:")
    for path in translated_files:
        print(path.resolve())


def cli(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    pdf_path = resolve_pdf_path(args.pdf_path)
    output_dir = resolve_output_dir(args.output_dir)
    asyncio.run(async_main(pdf_path, output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
