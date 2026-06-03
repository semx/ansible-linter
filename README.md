# Ansible Linter

[![tests](https://github.com/semx/ansible-linter/actions/workflows/tests.yml/badge.svg)](https://github.com/semx/ansible-linter/actions/workflows/tests.yml)

Small static analysis toolkit for Ansible playbooks and roles.

The linter focuses on operational safety rather than formatting. It scans YAML
files for risky task patterns that commonly cause non-idempotent runs, hidden
failures, accidental secret exposure, and production drift. Each rule mirrors an
upstream `ansible-lint` check or an Ansible core behaviour.

## Checks

- `ANS001` shell/command/raw tasks need a `changed_when`/`creates`/`removes` guard.
- `ANS002` `ignore_errors: true` should `register` the result or use `failed_when`.
- `ANS003` tasks that handle secrets should use `no_log: true`.
- `ANS004` package tasks should avoid `state: latest`.
- `ANS005` playbooks should avoid unbounded `hosts: all` without a limit hint.
- `ANS006` handlers should have stable names.
- `ANS007` role directories should include expected defaults, tasks, and metadata.
- `ANS008` file `mode` must be a quoted string (`mode: "0644"`), not raw octal.
- `ANS009` deprecated `sudo:` / `sudo_user:` should be `become` / `become_user`.
- `ANS010` `become_user` without `become` escalates nothing.
- `ANS011` `when: var == true` should be `when: var`.

Run `ansible-linter rules` for the catalogue, or see `docs/rules.md`.

## Quick start

```bash
python3 -m unittest discover -s tests
python3 -m ansible_linter.cli lint examples --pretty
```

Use `--fail-on warning` or `--fail-on error` in CI to turn findings into a
non-zero exit status. `--select`/`--ignore`/`--exclude`, a `.ansible-linter.toml`
config, and inline `# noqa: ANS005` suppression are documented in
`docs/configuration.md`.

## GitHub code scanning

`--format sarif` emits SARIF 2.1.0 that GitHub renders inline on pull requests:

```yaml
- run: python -m ansible_linter.cli lint playbooks --format sarif > ansible-linter.sarif
  continue-on-error: true
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: ansible-linter.sarif
```

A ready-made `code-scanning.yml` workflow ships in `.github/workflows/`.

## pre-commit and reusable Action

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/semx/ansible-linter
    rev: v0.1.0
    hooks:
      - id: ansible-linter
```

```yaml
# in a workflow
- uses: semx/ansible-linter@v0.1.0
  with:
    paths: playbooks roles
    fail-on: error
```

## Design

The scanner is dependency-light and does not require Ansible or PyYAML. It uses
line-oriented parsing that is conservative enough for CI guardrails and easy to
run in minimal containers.
