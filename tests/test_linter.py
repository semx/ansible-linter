import tempfile
from pathlib import Path
from unittest import TestCase

from ansible_linter.linter import AnsibleLinter


class AnsibleLinterTest(TestCase):
    def test_scans_directory_and_role_structure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            role = root / "roles" / "web"
            (role / "tasks").mkdir(parents=True)
            (role / "defaults").mkdir(parents=True)
            (role / "tasks" / "main.yml").write_text(
                "---\n- name: install latest\n  apt:\n    name: nginx\n    state: latest\n",
                encoding="utf-8",
            )
            (role / "defaults" / "main.yml").write_text("---\n", encoding="utf-8")

            report = AnsibleLinter().lint((str(root),))

        rule_ids = {finding.rule_id for finding in report.findings}
        self.assertEqual(report.files_checked, 2)
        self.assertIn("ANS004", rule_ids)
        self.assertIn("ANS007", rule_ids)

    def test_report_fail_threshold(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: app
  tasks:
    - name: hidden failure
      command: false
      ignore_errors: true
"""
        )

        self.assertTrue(report.should_fail("error"))
        self.assertTrue(report.should_fail("warning"))
        self.assertTrue(report.should_fail("info"))

    def test_handler_without_name_is_flagged(self) -> None:
        report = AnsibleLinter().lint_text(
            "---\n- service:\n    name: nginx\n    state: restarted\n",
            path="roles/web/handlers/main.yml",
        )

        self.assertIn("ANS006", {finding.rule_id for finding in report.findings})
