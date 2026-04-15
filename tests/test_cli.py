from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import Mock, patch

from mdtrans.cli import cli


class CliTests(unittest.TestCase):
    def test_returns_friendly_error_for_expected_failure(self) -> None:
        stderr = io.StringIO()
        with patch(
            "mdtrans.cli.resolve_pdf_path", return_value=Path("/tmp/in.pdf")
        ), patch(
            "mdtrans.cli.resolve_output_dir", return_value=Path("/tmp/out")
        ), patch(
            "mdtrans.cli.async_main", new_callable=Mock
        ) as async_main_mock, patch(
            "mdtrans.cli.asyncio.run"
        ) as asyncio_run_mock, redirect_stderr(stderr):
            asyncio_run_mock.side_effect = FileNotFoundError(
                "Created config template at /home/test/.config/mdtrans/config.toml. Please edit it and run again."
            )
            exit_code = cli(["in.pdf", "out"])
            async_main_mock.assert_called_once()

        self.assertEqual(exit_code, 1)
        self.assertEqual(
            stderr.getvalue().strip(),
            "Error: Created config template at /home/test/.config/mdtrans/config.toml. Please edit it and run again.",
        )

    def test_returns_zero_on_success(self) -> None:
        with patch(
            "mdtrans.cli.resolve_pdf_path", return_value=Path("/tmp/in.pdf")
        ), patch(
            "mdtrans.cli.resolve_output_dir", return_value=Path("/tmp/out")
        ), patch(
            "mdtrans.cli.async_main", new_callable=Mock
        ) as async_main_mock, patch(
            "mdtrans.cli.asyncio.run", return_value=None
        ):
            exit_code = cli(["in.pdf", "out"])
            async_main_mock.assert_called_once()

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
