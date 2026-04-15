from __future__ import annotations

from dataclasses import dataclass

from mdtrans.tokenizer import count_tokens


@dataclass(frozen=True)
class TranslationChunk:
    text: str
    token_count: int
    reason: str


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


def _split_by_units(text: str, token_budget: int, delimiters: list[str], reason: str) -> list[TranslationChunk]:
    if not text:
        return []

    token_count = count_tokens(text)
    if token_count <= token_budget:
        return [TranslationChunk(text=text, token_count=token_count, reason=reason)]

    if not delimiters:
        return [
            TranslationChunk(
                text=chunk,
                token_count=count_tokens(chunk),
                reason="token_budget_fallback",
            )
            for chunk in _split_by_char_budget(text, token_budget)
        ]

    delimiter = delimiters[0]
    units = _split_with_delimiter(text, delimiter)
    if len(units) <= 1:
        return _split_by_units(text, token_budget, delimiters[1:], reason)

    chunks: list[TranslationChunk] = []
    current = ""

    for unit in units:
        if not unit:
            continue

        if count_tokens(unit) > token_budget:
            if current:
                chunks.append(
                    TranslationChunk(
                        text=current,
                        token_count=count_tokens(current),
                        reason=reason,
                    )
                )
                current = ""
            chunks.extend(_split_by_units(unit, token_budget, delimiters[1:], reason))
            continue

        candidate = current + unit
        if current and count_tokens(candidate) > token_budget:
            chunks.append(
                TranslationChunk(
                    text=current,
                    token_count=count_tokens(current),
                    reason=reason,
                )
            )
            current = unit
        else:
            current = candidate

    if current:
        chunks.append(
            TranslationChunk(
                text=current,
                token_count=count_tokens(current),
                reason=reason,
            )
        )

    return chunks


def split_markdown_into_chunks(
    text: str,
    *,
    token_budget: int,
) -> list[TranslationChunk]:
    if token_budget <= 0:
        raise ValueError("token_budget must be a positive integer.")

    if not text:
        return []

    return _split_by_units(
        text,
        token_budget,
        delimiters=["\n\n", "\n"],
        reason="token_budget_split",
    )
