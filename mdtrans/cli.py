from __future__ import annotations

import argparse
import asyncio
import sys

from mdtrans.app import async_main
from mdtrans.discovery import resolve_output_dir, resolve_pdf_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mdtrans",
        description="Convert a PDF with MinerU and translate the generated Markdown into Simplified Chinese.",
    )
    parser.add_argument("pdf_path", help="Path to the source PDF file.")
    parser.add_argument(
        "output_dir",
        help="Directory where MinerU outputs and translated Markdown will be written.",
    )
    return parser.parse_args(argv)


def cli(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        pdf_path = resolve_pdf_path(args.pdf_path)
        output_dir = resolve_output_dir(args.output_dir)
        asyncio.run(async_main(pdf_path, output_dir))
        return 0
    except (FileNotFoundError, ValueError, EnvironmentError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
