from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mdtrans.config import DEFAULT_CONFIG_TEMPLATE, read_llm_config


class ConfigTests(unittest.TestCase):
    def _write_config(self, content: str) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = Path(tmpdir.name) / "config.toml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_reads_context_window(self) -> None:
        path = self._write_config(
            '[llm]\nbase_url = "https://api.example.com"\nmodel = "demo-model"\ncontext_window = 64000\nmax_output_tokens = 12000\nmax_chunk_tokens = 6000\n'
        )
        config = read_llm_config(path)
        self.assertEqual(config.context_window, 64000)
        self.assertEqual(config.max_output_tokens, 12000)
        self.assertEqual(config.max_chunk_tokens, 6000)

    def test_rejects_missing_context_window(self) -> None:
        path = self._write_config(
            '[llm]\nbase_url = "https://api.example.com"\nmodel = "demo-model"\n'
        )
        with self.assertRaises(ValueError):
            read_llm_config(path)

    def test_rejects_non_positive_context_window(self) -> None:
        path = self._write_config(
            '[llm]\nbase_url = "https://api.example.com"\nmodel = "demo-model"\ncontext_window = 0\nmax_output_tokens = 12000\n'
        )
        with self.assertRaises(ValueError):
            read_llm_config(path)

    def test_rejects_missing_max_output_tokens(self) -> None:
        path = self._write_config(
            '[llm]\nbase_url = "https://api.example.com"\nmodel = "demo-model"\ncontext_window = 64000\nmax_chunk_tokens = 6000\n'
        )
        with self.assertRaises(ValueError):
            read_llm_config(path)

    def test_rejects_missing_max_chunk_tokens(self) -> None:
        path = self._write_config(
            '[llm]\nbase_url = "https://api.example.com"\nmodel = "demo-model"\ncontext_window = 64000\nmax_output_tokens = 12000\n'
        )
        with self.assertRaises(ValueError):
            read_llm_config(path)

    def test_creates_template_when_config_is_missing(self) -> None:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = Path(tmpdir.name) / "nested" / "config.toml"

        with self.assertRaises(FileNotFoundError) as ctx:
            read_llm_config(path)

        self.assertTrue(path.exists())
        self.assertEqual(path.read_text(encoding="utf-8"), DEFAULT_CONFIG_TEMPLATE)
        self.assertIn("Created config template", str(ctx.exception))

    def test_does_not_overwrite_existing_invalid_config(self) -> None:
        path = self._write_config('[llm]\nbase_url = "https://api.example.com"\n')
        original = path.read_text(encoding="utf-8")

        with self.assertRaises(ValueError):
            read_llm_config(path)

        self.assertEqual(path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
