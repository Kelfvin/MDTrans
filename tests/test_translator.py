from __future__ import annotations

import unittest
from types import SimpleNamespace

from mdtrans.config import LLMConfig
from mdtrans.chunking import split_markdown_into_chunks
from mdtrans.translator import (
    normalize_block_math_markdown,
    normalize_html_table_markdown,
    normalize_translated_markdown,
    resolve_translation_token_budget,
    translate_chunk_with_retry,
)


class TranslatorBudgetTests(unittest.TestCase):
    def test_budget_is_limited_by_output_tokens(self) -> None:
        config = LLMConfig(
            base_url="https://api.example.com",
            model="demo-model",
            context_window=64000,
            max_output_tokens=12000,
            max_chunk_tokens=6000,
        )
        budget = resolve_translation_token_budget(config)
        self.assertEqual(budget, 6000)
        self.assertGreater(budget, 0)

    def test_rejects_too_small_output_budget(self) -> None:
        config = LLMConfig(
            base_url="https://api.example.com",
            model="demo-model",
            context_window=64000,
            max_output_tokens=256,
            max_chunk_tokens=128,
        )
        with self.assertRaises(ValueError):
            resolve_translation_token_budget(config)


class TranslatorNormalizationTests(unittest.TestCase):
    def test_normalizes_inline_joined_block_math(self) -> None:
        text = "详细过程如下：$$\na=b+c\n$$"
        normalized = normalize_block_math_markdown(text)
        self.assertEqual(normalized, "详细过程如下：\n\n$$\na=b+c\n$$")

    def test_splits_collapsed_adjacent_block_math(self) -> None:
        text = "$$\na\n$$$$\nb\n$$"
        normalized = normalize_block_math_markdown(text)
        self.assertEqual(normalized, "$$\na\n$$\n\n$$\nb\n$$")

    def test_normalizes_formula_before_heading(self) -> None:
        text = "$$\na=b+c\n$$# III. 实验"
        normalized = normalize_block_math_markdown(text)
        self.assertEqual(normalized, "$$\na=b+c\n$$\n\n# III. 实验")

    def test_leaves_inline_math_unchanged(self) -> None:
        text = "这是 $x+y$ 的例子。"
        normalized = normalize_block_math_markdown(text)
        self.assertEqual(normalized, text)

    def test_normalizes_text_before_html_table(self) -> None:
        text = "最优结果标出。<table><tr><td>x</td></tr></table>"
        normalized = normalize_html_table_markdown(text)
        self.assertEqual(
            normalized,
            "最优结果标出。\n\n<table><tr><td>x</td></tr></table>",
        )

    def test_normalizes_html_table_before_heading(self) -> None:
        text = "<table><tr><td>x</td></tr></table># III. 实验"
        normalized = normalize_html_table_markdown(text)
        self.assertEqual(
            normalized,
            "<table><tr><td>x</td></tr></table>\n\n# III. 实验",
        )

    def test_normalizes_html_table_before_image(self) -> None:
        text = "<table><tr><td>x</td></tr></table>![](image.png)"
        normalized = normalize_html_table_markdown(text)
        self.assertEqual(
            normalized,
            "<table><tr><td>x</td></tr></table>\n\n![](image.png)",
        )

    def test_combined_normalization_repairs_math_and_table(self) -> None:
        text = "说明：$$\na=b\n$$表格如下。<table><tr><td>x</td></tr></table># III. 实验"
        normalized = normalize_translated_markdown(text)
        self.assertEqual(
            normalized,
            "说明：\n\n$$\na=b\n$$\n\n表格如下。\n\n<table><tr><td>x</td></tr></table>\n\n# III. 实验",
        )


class _FakeLLM:
    def __init__(self, finish_reasons: list[str | None]) -> None:
        self.finish_reasons = finish_reasons
        self.calls: list[str] = []

    async def ainvoke(self, messages):
        text = messages[-1].content
        self.calls.append(text)
        finish_reason = self.finish_reasons.pop(0)
        return SimpleNamespace(content=text, response_metadata={"finish_reason": finish_reason})


class TranslatorRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_retries_truncated_chunk_by_splitting(self) -> None:
        text = "# Title\n\nAlpha.\n\nBeta.\n\nGamma.\n"
        chunks = split_markdown_into_chunks(text, token_budget=1000)
        llm = _FakeLLM(["length", "stop", "stop"])
        translated = await translate_chunk_with_retry(llm, chunks[0], 1000, label="1")
        self.assertEqual(translated, text)
        self.assertEqual(len(llm.calls), 3)

    async def test_raises_when_chunk_cannot_be_split_further(self) -> None:
        chunk = split_markdown_into_chunks("single", token_budget=1000)[0]
        llm = _FakeLLM(["length"] * 20)
        with self.assertRaises(RuntimeError):
            await translate_chunk_with_retry(llm, chunk, 1, label="1")


if __name__ == "__main__":
    unittest.main()
