import os
import tempfile
from pathlib import Path
from unittest import TestCase

from ansible_linter.config import load_file_config


class LoadFileConfigTest(TestCase):
    def test_no_path_without_default_file_returns_empty(self) -> None:
        previous = os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            os.chdir(directory)
            try:
                self.assertEqual(load_file_config(None), {})
            finally:
                os.chdir(previous)

    def test_reads_ansible_linter_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cfg.toml"
            path.write_text(
                '[ansible_linter]\nignore = ["ANS005"]\nfail_on = "warning"\n',
                encoding="utf-8",
            )

            config = load_file_config(path)

        self.assertEqual(config["ignore"], ["ANS005"])
        self.assertEqual(config["fail_on"], "warning")

    def test_reads_tool_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pyproject.toml"
            path.write_text('[tool.ansible_linter]\nselect = ["ANS001"]\n', encoding="utf-8")

            config = load_file_config(path)

        self.assertEqual(config["select"], ["ANS001"])

    def test_missing_explicit_path_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_file_config("/nonexistent/cfg.toml")
