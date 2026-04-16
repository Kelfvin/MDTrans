# MDTrans

[简体中文](./README.zh.md) | English

## Overview

**Convert any English PDF document into Chinese Markdown.**

MDTrans supports both digitally generated PDFs and scanned PDFs. It preserves the structure of the source PDF, including text, headings, lists, and tables, and translates the content into Simplified Chinese. Because translation uses a larger model context window, MDTrans usually achieves better document-level consistency and overall translation quality than typical short-context translation tools. The final translated Markdown file is written beside the original Markdown with a `.zh.md` suffix.

## How It Works

MDTrans first calls the official `mineru` CLI from an async Python subprocess to convert a PDF into Markdown, including MinerU's scanned-document workflow, then uses LangChain and an OpenAI-compatible chat model to translate the generated Markdown into Simplified Chinese with larger document context instead of fragmented sentence-by-sentence translation.

## Requirements

- A GPU capable of running MinerU, ideally with at least 16 GB of VRAM

## Installation

1. Install MinerU first, because MDTrans depends on it to parse PDFs into Markdown:

```bash
uv tool install "mineru[core,vllm]"
```

2. Install MDTrans:

```bash
uv tool install mdtrans
```

## Configuration

The configuration file is located at `~/.config/mdtrans/config.toml`. The program will create it on the first run, or you can choose to create it manually.

```toml
[llm]
base_url = "https://api.deepseek.com"
model = "deepseek-chat"
context_window = 64000
max_output_tokens = 8000
max_chunk_tokens = 5000
```

The Xiaomi `mimo-flash` model is a good choice when available, with a strong balance between translation quality and speed.

## Usage

Because MDTrans relies on an OpenAI-compatible API for translation, you must set the `OPENAI_API_KEY` environment variable to your API key before running it:

```bash
export OPENAI_API_KEY="your-api-key"
```

```bash
mdtrans /path/to/input.pdf /path/to/output-dir
```

> [!WARNING]
> On the first launch, MinerU may need to download some model files, so startup can be slow.

The tool runs in this order:

1. Accept the source PDF path as the first positional argument
2. Accept the output directory as the second positional argument
3. Run `mineru -p <selected-pdf> -o <output-dir> -b hybrid-auto-engine`
4. Discover the generated Markdown files under the chosen output directory
5. Write translated Chinese copies as `*.zh.md` beside the original Markdown files

## Roadmap

- [x] Basic translation support
- [ ] Service and Docker deployment: package MDTrans as a RESTful API service and provide a Docker image for easier deployment and usage.
- [ ] Long-document translation: build an agent-based workflow to support very long documents, including 300+ pages.
- [ ] Evaluation and optimization of translation performance across different models.
- [ ] Support for more target languages, such as Japanese and Korean.
- [ ] More translation options, such as formal/informal tone and terminology handling.

## Disclaimer

MDTrans is designed to provide a convenient PDF-to-Markdown translation workflow, but translation quality can still be affected by model capability, document complexity, and context window limits. For important or sensitive documents, it is recommended that you manually review and polish the output after the initial translation to ensure accuracy and readability. MDTrans is not responsible for any loss or misunderstanding caused by translation errors.
