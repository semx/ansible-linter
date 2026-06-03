import tempfile
from pathlib import Path
from unittest import TestCase

from ansible_linter.linter import AnsibleLinter, LintConfig

PLAYBOOK = """
---
- hosts: all
  tasks:
    - name: restart
      shell: systemctl restart app
"""


class NoqaTest(TestCase):
    def test_targeted_noqa_suppresses_one_rule(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: all  # noqa: ANS005
  tasks: []
"""
        )

        self.assertNotIn("ANS005", {finding.rule_id for finding in report.findings})

    def test_bare_noqa_suppresses_all_rules_on_line(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: all  # noqa
  tasks: []
"""
        )

        self.assertEqual(report.findings, ())

    def test_noqa_only_affects_listed_rule(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: all  # noqa: ANS001
  tasks: []
"""
        )

        self.assertIn("ANS005", {finding.rule_id for finding in report.findings})


class SelectIgnoreTest(TestCase):
    def test_select_keeps_only_requested_rules(self) -> None:
        config = LintConfig(select=("ANS001",))
        report = AnsibleLinter(config=config).lint_text(PLAYBOOK)

        self.assertEqual({finding.rule_id for finding in report.findings}, {"ANS001"})

    def test_ignore_drops_requested_rules(self) -> None:
        config = LintConfig(ignore=("ANS005",))
        report = AnsibleLinter(config=config).lint_text(PLAYBOOK)

        self.assertNotIn("ANS005", {finding.rule_id for finding in report.findings})


class ExcludeTest(TestCase):
    def test_exclude_skips_matching_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "keep.yml").write_text("---\n- hosts: all\n  tasks: []\n", encoding="utf-8")
            (root / "skip.yml").write_text("---\n- hosts: all\n  tasks: []\n", encoding="utf-8")

            config = LintConfig(exclude=("*skip.yml",))
            report = AnsibleLinter(config=config).lint((str(root),))

        self.assertEqual(report.files_checked, 1)
        self.assertTrue(all("skip.yml" not in finding.path for finding in report.findings))
