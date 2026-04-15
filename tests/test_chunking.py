from __future__ import annotations

import unittest

from mdtrans.chunking import split_markdown_into_chunks


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


if __name__ == "__main__":
    unittest.main()
