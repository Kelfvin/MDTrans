from __future__ import annotations

import unittest

from mdtrans.chunking import parse_blocks, split_markdown_into_chunks


class ChunkingTests(unittest.TestCase):
    def test_returns_single_chunk_when_text_fits_budget(self) -> None:
        text = "# Title\n\nParagraph\n\n```python\nprint('x')\n```\n"
        chunks = split_markdown_into_chunks(text, token_budget=1000)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, text)

    def test_preserves_original_text_when_split(self) -> None:
        text = "# Title\n\n" + ("alpha beta gamma\n" * 40) + "\n$$\na=b+c\n$$\n"
        chunks = split_markdown_into_chunks(text, token_budget=40)
        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunk.text for chunk in chunks), text)
        self.assertTrue(all(chunk.token_count <= 40 for chunk in chunks))

    def test_falls_back_when_no_blank_lines_exist(self) -> None:
        text = "line\n" * 200
        chunks = split_markdown_into_chunks(text, token_budget=20)
        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunk.text for chunk in chunks), text)

    def test_parses_markdown_blocks(self) -> None:
        text = (
            "# Title\n\n"
            "Paragraph one.\n\n"
            "```python\nprint('x')\n```\n\n"
            "<table><tr><td>x</td></tr></table>\n"
        )
        blocks = parse_blocks(text)
        self.assertEqual("".join(block.text for block in blocks), text)
        self.assertEqual(
            [block.kind for block in blocks],
            ["heading", "paragraph", "fence", "html_block"],
        )

    def test_greedy_packs_by_block_boundaries(self) -> None:
        text = (
            "# Title\n\n"
            "First paragraph.\n\n"
            "Second paragraph.\n\n"
            "```python\nprint('x')\n```\n"
        )
        blocks = parse_blocks(text)
        budget = blocks[0].token_count + blocks[1].token_count
        chunks = split_markdown_into_chunks(text, token_budget=budget)
        self.assertEqual(len(chunks), 4)
        self.assertEqual(chunks[0].block_kinds, ("heading", "paragraph"))
        self.assertEqual(chunks[1].block_kinds, ("paragraph",))
        self.assertEqual(chunks[2].reason, "oversized_block_line_split")
        self.assertEqual(chunks[3].reason, "oversized_block_line_split")
        self.assertEqual("".join(chunk.text for chunk in chunks), text)


if __name__ == "__main__":
    unittest.main()
