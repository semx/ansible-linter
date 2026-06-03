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

    def test_ignore_errors_allowed_with_register(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: app
  tasks:
    - name: probe
      command: systemctl status app
      register: probe
      ignore_errors: true
"""
        )

        self.assertNotIn("ANS002", {finding.rule_id for finding in report.findings})

    def test_when_is_not_an_idempotency_guard(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: app
  tasks:
    - name: maybe restart
      shell: systemctl restart app
      when: should_restart
"""
        )

        self.assertIn("ANS001", {finding.rule_id for finding in report.findings})

    def test_flags_unquoted_octal_mode(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: app
  tasks:
    - name: place file
      file:
        path: /etc/app.conf
        mode: 0644
"""
        )

        self.assertIn("ANS008", {finding.rule_id for finding in report.findings})

    def test_allows_quoted_mode(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: app
  tasks:
    - name: place file
      file:
        path: /etc/app.conf
        mode: "0644"
"""
        )

        self.assertNotIn("ANS008", {finding.rule_id for finding in report.findings})

    def test_flags_deprecated_sudo(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: app
  tasks:
    - name: legacy escalation
      sudo: true
      command: whoami
      changed_when: false
"""
        )

        self.assertIn("ANS009", {finding.rule_id for finding in report.findings})

    def test_flags_become_user_without_become(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: app
  tasks:
    - name: run as postgres
      become_user: postgres
      command: psql -c 'select 1'
      changed_when: false
"""
        )

        self.assertIn("ANS010", {finding.rule_id for finding in report.findings})

    def test_allows_become_user_with_become(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: app
  tasks:
    - name: run as postgres
      become: true
      become_user: postgres
      command: psql -c 'select 1'
      changed_when: false
"""
        )

        self.assertNotIn("ANS010", {finding.rule_id for finding in report.findings})

    def test_flags_literal_boolean_comparison(self) -> None:
        report = AnsibleLinter().lint_text(
            """
---
- hosts: app
  tasks:
    - name: conditional
      debug:
        msg: hi
      when: feature_enabled == true
"""
        )

        self.assertIn("ANS011", {finding.rule_id for finding in report.findings})
