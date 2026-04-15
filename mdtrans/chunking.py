from __future__ import annotations

from dataclasses import dataclass

from markdown_it import MarkdownIt
from markdown_it.token import Token

from mdtrans.tokenizer import count_tokens


@dataclass(frozen=True)
class MarkdownBlock:
    kind: str
    text: str
    token_count: int
    start_line: int
    end_line: int


@dataclass(frozen=True)
class TranslationChunk:
    text: str
    token_count: int
    reason: str
    block_count: int
    block_kinds: tuple[str, ...]
    source_blocks: tuple[MarkdownBlock, ...] = ()


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for idx, char in enumerate(text):
        if char == "\n":
            starts.append(idx + 1)
    return starts


def _offset_for_line(line_starts: list[int], line_no: int) -> int:
    if line_no <= 0:
        return 0
    if line_no >= len(line_starts):
        return line_starts[-1] if line_starts else 0
    return line_starts[line_no]


def _extract_block_text(
    text: str, line_starts: list[int], start_line: int, end_line: int
) -> str:
    start_offset = _offset_for_line(line_starts, start_line)
    end_offset = (
        len(text)
        if end_line >= len(line_starts)
        else _offset_for_line(line_starts, end_line)
    )
    return text[start_offset:end_offset]


def _token_block_kind(token: Token) -> str:
    if token.type in {"fence", "code_block", "html_block", "hr"}:
        return token.type
    if token.type.endswith("_open"):
        return token.type.removesuffix("_open")
    return token.type


def _build_block(
    text: str,
    line_starts: list[int],
    token: Token,
    start_line: int,
    end_line: int,
) -> MarkdownBlock:
    block_text = _extract_block_text(text, line_starts, start_line, end_line)
    return MarkdownBlock(
        kind=_token_block_kind(token),
        text=block_text,
        token_count=count_tokens(block_text),
        start_line=start_line,
        end_line=end_line,
    )


def parse_blocks(text: str) -> list[MarkdownBlock]:
    if not text:
        return []

    md = MarkdownIt()
    tokens = md.parse(text)
    line_starts = _line_starts(text)
    blocks: list[MarkdownBlock] = []
    stack: list[Token] = []

    for token in tokens:
        if token.level != 0:
            continue

        if token.type in {"fence", "code_block", "html_block", "hr"}:
            if token.map is None:
                continue
            start_line, end_line = token.map
            blocks.append(_build_block(text, line_starts, token, start_line, end_line))
            continue

        if token.nesting == 1 and token.map is not None and token.type.endswith("_open"):
            stack.append(token)
            continue

        if token.nesting == -1 and token.type.endswith("_close"):
            if not stack:
                continue
            open_token = stack.pop()
            if open_token.type.removesuffix("_open") != token.type.removesuffix("_close"):
                continue
            if open_token.map is None:
                continue
            start_line, end_line = open_token.map
            blocks.append(
                _build_block(text, line_starts, open_token, start_line, end_line)
            )

    blocks.sort(key=lambda block: (block.start_line, block.end_line))

    deduped: list[MarkdownBlock] = []
    seen: set[tuple[int, int, str]] = set()
    for block in blocks:
        key = (block.start_line, block.end_line, block.kind)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(block)

    adjusted: list[MarkdownBlock] = []
    total_lines = len(line_starts)
    for idx, block in enumerate(deduped):
        next_start_line = (
            deduped[idx + 1].start_line if idx + 1 < len(deduped) else total_lines
        )
        block_text = _extract_block_text(text, line_starts, block.start_line, next_start_line)
        adjusted.append(
            MarkdownBlock(
                kind=block.kind,
                text=block_text,
                token_count=count_tokens(block_text),
                start_line=block.start_line,
                end_line=next_start_line,
            )
        )
    return adjusted


def _split_with_delimiter(text: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    start = 0
    delim_len = len(delimiter)

    while True:
        idx = text.find(delimiter, start)
        if idx == -1:
            tail = text[start:]
            if tail:
                parts.append(tail)
            break
        end = idx + delim_len
        parts.append(text[start:end])
        start = end

    return parts


def _split_by_char_budget(text: str, token_budget: int) -> list[str]:
    chunks: list[str] = []
    start = 0

    while start < len(text):
        low = start + 1
        high = len(text)
        best_end = low

        while low <= high:
            mid = (low + high) // 2
            candidate = text[start:mid]
            if count_tokens(candidate) <= token_budget:
                best_end = mid
                low = mid + 1
            else:
                high = mid - 1

        if best_end <= start:
            best_end = start + 1

        chunks.append(text[start:best_end])
        start = best_end

    return chunks


def _make_chunk(
    text: str,
    reason: str,
    block_kinds: list[str],
    block_count: int,
    source_blocks: tuple[MarkdownBlock, ...] = (),
) -> TranslationChunk:
    return TranslationChunk(
        text=text,
        token_count=count_tokens(text),
        reason=reason,
        block_count=block_count,
        block_kinds=tuple(block_kinds),
        source_blocks=source_blocks,
    )


def _chunk_from_blocks(blocks: list[MarkdownBlock], reason: str) -> TranslationChunk:
    return _make_chunk(
        text="".join(block.text for block in blocks),
        reason=reason,
        block_kinds=[block.kind for block in blocks],
        block_count=len(blocks),
        source_blocks=tuple(blocks),
    )


def _split_text_fallback(
    text: str, token_budget: int, reason: str, kind: str
) -> list[TranslationChunk]:
    if not text:
        return []

    token_count = count_tokens(text)
    if token_count <= token_budget:
        return [_make_chunk(text, reason, [kind], 1)]

    for delimiter, split_reason in (
        ("\n\n", "oversized_block_paragraph_split"),
        ("\n", "oversized_block_line_split"),
    ):
        units = _split_with_delimiter(text, delimiter)
        if len(units) <= 1:
            continue

        chunks: list[TranslationChunk] = []
        current = ""
        for unit in units:
            if not unit:
                continue
            unit_tokens = count_tokens(unit)
            if unit_tokens > token_budget:
                if current:
                    chunks.append(_make_chunk(current, split_reason, [kind], 1))
                    current = ""
                chunks.extend(_split_text_fallback(unit, token_budget, split_reason, kind))
                continue

            candidate = current + unit
            if current and count_tokens(candidate) > token_budget:
                chunks.append(_make_chunk(current, split_reason, [kind], 1))
                current = unit
            else:
                current = candidate

        if current:
            chunks.append(_make_chunk(current, split_reason, [kind], 1))
        if chunks:
            return chunks

    return [
        _make_chunk(chunk, "token_budget_fallback", [kind], 1)
        for chunk in _split_by_char_budget(text, token_budget)
    ]


def _split_oversized_block(block: MarkdownBlock, token_budget: int) -> list[TranslationChunk]:
    return _split_text_fallback(
        block.text, token_budget, "oversized_block_paragraph_split", block.kind
    )


def group_blocks_into_chunks(
    blocks: list[MarkdownBlock], token_budget: int
) -> list[TranslationChunk]:
    chunks: list[TranslationChunk] = []
    current_text = ""
    current_token_count = 0
    current_block_count = 0
    current_block_kinds: list[str] = []
    current_blocks: list[MarkdownBlock] = []

    def flush() -> None:
        nonlocal current_text, current_token_count, current_block_count, current_block_kinds, current_blocks
        if not current_text:
            return
        chunks.append(
            _make_chunk(
                current_text,
                "block_greedy_pack",
                current_block_kinds,
                current_block_count,
                tuple(current_blocks),
            )
        )
        current_text = ""
        current_token_count = 0
        current_block_count = 0
        current_block_kinds = []
        current_blocks = []

    for block in blocks:
        if block.token_count > token_budget:
            flush()
            chunks.extend(_split_oversized_block(block, token_budget))
            continue

        candidate_text = current_text + block.text
        candidate_tokens = (
            count_tokens(candidate_text) if current_text else block.token_count
        )
        if current_text and candidate_tokens > token_budget:
            flush()
            candidate_text = block.text
            candidate_tokens = block.token_count

        current_text = candidate_text
        current_token_count = candidate_tokens
        current_block_count += 1
        current_block_kinds.append(block.kind)
        current_blocks.append(block)

    flush()
    return chunks


def split_markdown_into_chunks(text: str, *, token_budget: int) -> list[TranslationChunk]:
    if token_budget <= 0:
        raise ValueError("token_budget must be a positive integer.")
    if not text:
        return []

    blocks = parse_blocks(text)
    if not blocks:
        return _split_text_fallback(text, token_budget, "token_budget_split", "document")
    return group_blocks_into_chunks(blocks, token_budget)


def split_chunk_for_retry(chunk: TranslationChunk, token_budget: int) -> list[TranslationChunk]:
    if chunk.block_count > 1:
        blocks = list(chunk.source_blocks) if chunk.source_blocks else parse_blocks(chunk.text)
        if len(blocks) > 1:
            midpoint = len(blocks) // 2
            return [
                _chunk_from_blocks(blocks[:midpoint], "retry_block_split"),
                _chunk_from_blocks(blocks[midpoint:], "retry_block_split"),
            ]

    smaller_budget = max(1, min(token_budget, chunk.token_count // 2))
    if smaller_budget >= chunk.token_count:
        smaller_budget = max(1, chunk.token_count - 1)

    retry_chunks = split_markdown_into_chunks(chunk.text, token_budget=smaller_budget)
    if len(retry_chunks) == 1 and retry_chunks[0].text == chunk.text:
        raise ValueError("Unable to split truncated chunk into smaller retry chunks.")
    return retry_chunks
