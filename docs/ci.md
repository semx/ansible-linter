# CI Usage

Run the linter against playbooks and roles before deployment:

```bash
python -m ansible_linter.cli lint playbooks roles --format text --fail-on error
```

For stricter repositories, fail on warnings:

```bash
python -m ansible_linter.cli lint playbooks roles --pretty --fail-on warning
```

The linter exits with:

- `0` when no finding meets the configured threshold.
- `1` when at least one finding meets the configured threshold.
- `2` for CLI usage errors.
