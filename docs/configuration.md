# Configuration

## Selecting rules

```bash
ansible-linter lint playbooks --select ANS001,ANS010   # run only these rules
ansible-linter lint playbooks --ignore ANS005          # run everything except these
ansible-linter lint playbooks --exclude '*/vendor/*'   # skip matching paths (repeatable)
```

`--select` and `--ignore` take comma-separated rule ids. `--exclude` takes a glob
matched against each file or role path and may be passed more than once.

## Config file

Settings can live in a `.ansible-linter.toml` discovered in the working directory,
or any path passed with `--config`. Both a top-level `[ansible_linter]` table and a
pyproject-style `[tool.ansible_linter]` table are accepted.

```toml
[ansible_linter]
select = []                # empty = all rules
ignore = ["ANS005"]
exclude = ["*/molecule/*"]
fail_on = "error"          # info | warning | error
role_structure = true      # check tasks/defaults/meta presence
```

Command-line flags override the config file.

## Inline suppression

Use `# noqa` on the reported line (see `docs/rules.md`).

## Output formats

```bash
ansible-linter lint playbooks --format text     # human readable
ansible-linter lint playbooks --format json     # machine readable
ansible-linter lint playbooks --format sarif     # SARIF 2.1.0 for code scanning
```

## Rule catalogue

```bash
ansible-linter rules                 # id, severity, summary
ansible-linter rules --format json
ansible-linter --version
```
