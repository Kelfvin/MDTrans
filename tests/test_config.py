from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mdtrans.config import read_llm_config


class ConfigTests(unittest.TestCase):
    def _write_config(self, content: str) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = Path(tmpdir.name) / "config.toml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_reads_context_window(self) -> None:
        path = self._write_config(
            '[llm]\nbase_url = "https://api.example.com"\nmodel = "demo-model"\ncontext_window = 64000\n'
        )
        config = read_llm_config(path)
        self.assertEqual(config.context_window, 64000)

    def test_rejects_missing_context_window(self) -> None:
        path = self._write_config(
            '[llm]\nbase_url = "https://api.example.com"\nmodel = "demo-model"\n'
        )
        with self.assertRaises(ValueError):
            read_llm_config(path)

    def test_rejects_non_positive_context_window(self) -> None:
        path = self._write_config(
            '[llm]\nbase_url = "https://api.example.com"\nmodel = "demo-model"\ncontext_window = 0\n'
        )
        with self.assertRaises(ValueError):
            read_llm_config(path)


if __name__ == "__main__":
    unittest.main()
