from unittest import TestCase

from ansible_linter.linter import AnsibleLinter


class RuleSetTest(TestCase):
    def test_flags_shell_without_idempotency_guard(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: app
  tasks:
    - name: restart app
      shell: systemctl restart app
"""
        )

        self.assertIn("ANS001", {finding.rule_id for finding in report.findings})

    def test_allows_shell_with_changed_when(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: app
  tasks:
    - name: inspect status
      command: systemctl status app
      changed_when: false
"""
        )

        self.assertNotIn("ANS001", {finding.rule_id for finding in report.findings})

    def test_flags_ignore_errors_as_error(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: app
  tasks:
    - name: hide failure
      command: systemctl status app
      ignore_errors: true
"""
        )

        finding = next(item for item in report.findings if item.rule_id == "ANS002")
        self.assertEqual(finding.severity, "error")

    def test_flags_secret_without_no_log(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: app
  tasks:
    - name: write password
      copy:
        content: "{{ database_password }}"
        dest: /etc/app/password
"""
        )

        self.assertIn("ANS003", {finding.rule_id for finding in report.findings})

    def test_allows_secret_with_no_log(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: app
  tasks:
    - name: write password
      no_log: true
      copy:
        content: "{{ database_password }}"
        dest: /etc/app/password
"""
        )

        self.assertNotIn("ANS003", {finding.rule_id for finding in report.findings})

    def test_flags_latest_package_state(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: app
  tasks:
    - name: install package
      apt:
        name: nginx
        state: latest
"""
        )

        self.assertIn("ANS004", {finding.rule_id for finding in report.findings})

    def test_flags_hosts_all_without_limit(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: all
  tasks: []
"""
        )

        self.assertIn("ANS005", {finding.rule_id for finding in report.findings})
