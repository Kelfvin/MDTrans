from __future__ import annotations

from pathlib import Path

from mdtrans.config import read_llm_config, require_openai_api_key
from mdtrans.mineru_runner import run_mineru
from mdtrans.translator import translate_mineru_outputs


async def async_main(pdf_path: Path, output_dir: Path) -> None:
    llm_config = read_llm_config()
    require_openai_api_key()
    print(f"Using input PDF: {pdf_path}")

    # Run MinerU to generate Markdown outputs
    await run_mineru(pdf_path, output_dir)
    print(f"MinerU output directory: {output_dir}")

    # Translate the MinerU output Markdown files
    translated_files = await translate_mineru_outputs(pdf_path, output_dir, llm_config)
    print("Chinese Markdown outputs:")
    for path in translated_files:
        print(path.resolve())
