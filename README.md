# Ansible Linter

Small static analysis toolkit for Ansible playbooks and roles.

The linter focuses on operational safety rather than formatting. It scans YAML
files for risky task patterns that commonly cause non-idempotent runs, hidden
failures, accidental secret exposure, and production drift.

## Checks

- `ANS001` shell and command tasks should define idempotency guards.
- `ANS002` `ignore_errors: true` should not hide failed automation.
- `ANS003` tasks that handle secrets should use `no_log: true`.
- `ANS004` package tasks should avoid `state: latest`.
- `ANS005` playbooks should avoid unbounded `hosts: all` without a limit hint.
- `ANS006` handlers should have stable names.
- `ANS007` role directories should include expected defaults, tasks, and metadata.

## Quick start

```bash
python3 -m unittest discover -s tests
python3 -m ansible_linter.cli lint examples --pretty
```

Use `--fail-on warning` or `--fail-on error` in CI to turn findings into a
non-zero exit status.

## Design

The scanner is dependency-light and does not require Ansible or PyYAML. It uses
line-oriented parsing that is conservative enough for CI guardrails and easy to
run in minimal containers.
