import io
import json
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

    def test_sarif_format_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "playbook.yml"
            path.write_text("---\n- hosts: all\n  tasks: []\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                status = main(["lint", str(path), "--format", "sarif"])

        document = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(document["version"], "2.1.0")
        run = document["runs"][0]
        self.assertEqual(run["tool"]["driver"]["name"], "ansible-linter")
        self.assertTrue(any(result["ruleId"] == "ANS005" for result in run["results"]))

    def test_ignore_flag_suppresses_rule(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "playbook.yml"
            path.write_text("---\n- hosts: all\n  tasks: []\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                status = main(["lint", str(path), "--ignore", "ANS005", "--fail-on", "error"])

        self.assertEqual(status, 0)
        self.assertNotIn("ANS005", output.getvalue())

    def test_rules_subcommand_lists_rules(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["rules", "--format", "json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        ids = {rule["id"] for rule in payload}
        self.assertIn("ANS001", ids)
        self.assertIn("ANS011", ids)

    def test_version_flag(self) -> None:
        output = io.StringIO()
        with self.assertRaises(SystemExit) as caught, redirect_stdout(output):
            main(["--version"])

        self.assertEqual(caught.exception.code, 0)
        self.assertIn("ansible-linter", output.getvalue())
