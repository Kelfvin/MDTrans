# MDTrans

[简体中文](./README.zh.md) | English

## Overview

**Convert any English PDF document into Chinese Markdown.**

MDTrans preserves the document structure from the source PDF, including text, headings, lists, and tables, and translates the content into Simplified Chinese. The final translated Markdown file is written beside the original Markdown with a `.zh.md` suffix.

## How It Works

MDTrans first calls the official `mineru` CLI from an async Python subprocess to convert a PDF into Markdown, then uses LangChain and an OpenAI-compatible chat model to translate the generated Markdown into Simplified Chinese.

## Requirements

- A GPU capable of running MinerU, ideally with at least 16 GB of VRAM

## Installation

```bash
uv tool install mdtrans
```

## Configuration

The configuration file is located at `~/.config/mdtrans/config.toml`. If it does not exist, MDTrans creates a template for you on first run.

```toml
[llm]
base_url = "https://api.deepseek.com"
model = "deepseek-chat"
context_window = 64000
max_output_tokens = 8000
max_chunk_tokens = 5000
```

The `mimo-flash` model from Xiaomi is a good default choice when available, with a strong balance between translation quality and speed.

## Usage

MDTrans relies on an OpenAI-compatible API, so you must export `OPENAI_API_KEY` before running it:

```bash
export OPENAI_API_KEY="your-api-key"
```

```bash
mdtrans /path/to/input.pdf /path/to/output-dir
```

The tool runs in this order:

1. Accept the source PDF path as the first positional argument
2. Accept the output directory as the second positional argument
3. Run `mineru -p <selected-pdf> -o <output-dir> -b hybrid-auto-engine`
4. Discover the generated Markdown files under the chosen output directory
5. Write translated Chinese copies as `*.zh.md` beside the original Markdown files
