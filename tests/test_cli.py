import io
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import TestCase

from ansible_linter.cli import main


class CliTest(TestCase):
    def test_lint_returns_non_zero_on_error_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "playbook.yml"
            path.write_text(
                """
---
- hosts: app
  tasks:
    - name: hidden failure
      command: false
      ignore_errors: true
""",
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                status = main(["lint", str(path), "--fail-on", "error"])

        self.assertEqual(status, 1)
        self.assertIn("ANS002", output.getvalue())

    def test_text_format_outputs_human_readable_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "playbook.yml"
            path.write_text("---\n- hosts: all\n  tasks: []\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                status = main(["lint", str(path), "--format", "text", "--fail-on", "error"])

        self.assertEqual(status, 0)
        self.assertIn("WARNING ANS005", output.getvalue())
