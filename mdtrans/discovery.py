from __future__ import annotations

from pathlib import Path


def resolve_pdf_path(pdf_path_arg: str) -> Path:
    pdf_path = Path(pdf_path_arg).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"Input PDF not found: {pdf_path}")
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Input PDF is not a file: {pdf_path}")
    return pdf_path


def resolve_output_dir(output_dir_arg: str) -> Path:
    return Path(output_dir_arg).expanduser().resolve()


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
