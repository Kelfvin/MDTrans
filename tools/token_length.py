from __future__ import annotations

import argparse
from pathlib import Path

from mdtrans.tokenizer import ENCODING_NAME, count_tokens


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calculate token length for a single UTF-8 text or Markdown file.",
    )
    parser.add_argument("file", help="Path to the input file.")
    return parser.parse_args(argv)


def resolve_file(path_arg: str) -> Path:
    path = Path(path_arg).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"Input path is not a file: {path}")
    return path


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Input file is not valid UTF-8 text: {path}") from exc

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    file_path = resolve_file(args.file)
    text = read_text(file_path)
    token_count = count_tokens(text)
    char_count = len(text)
    line_count = text.count("\n") + (1 if text else 0)

    print(f"file: {file_path}")
    print(f"encoding: {ENCODING_NAME}")
    print(f"characters: {char_count}")
    print(f"lines: {line_count}")
    print(f"tokens: {token_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
