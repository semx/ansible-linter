# Rules

The rule identifiers are stable. Each rule mirrors a check from the upstream
[`ansible-lint`](https://ansible.readthedocs.io/projects/lint/) project or an
Ansible core behaviour, restated for dependency-light line-oriented scanning.

## ANS001 — shell idempotency (warning)

Shell-like tasks (`shell`, `command`, `raw`) should be guarded by `changed_when`,
`creates`, or `removes`. These are the only guards that change how the task
reports `changed`; `when` and `check_mode` do not, so they are not accepted.
Mirrors `no-changed-when`.

## ANS002 — unguarded ignore_errors (error)

`ignore_errors: true` hides automation failures. It is allowed when the task also
sets `register:` so the result can be inspected; otherwise prefer `failed_when`
or a `rescue` block. Mirrors `ignore-errors`.

## ANS003 — secret without no_log (error)

Tasks that contain secret-looking words should set `no_log: true`.

## ANS004 — package state: latest (warning)

Package tasks should avoid `state: latest` because it makes runs depend on
repository state at execution time. Mirrors `package-latest`.

## ANS005 — unbounded hosts: all (warning)

`hosts: all` should be paired with a rollout limit such as `serial`, a narrower
group, or an explicit `# ansible-linter: allow hosts-all` comment.

## ANS006 — unnamed handler (warning)

Handlers should have stable names for reliable `notify` references.

## ANS007 — role structure (warning)

Role directories should include `tasks/main.yml`, `defaults/main.yml`, and
`meta/main.yml`.

## ANS008 — unquoted octal mode (error)

`mode: 0644` (or `mode: 644`) is parsed by YAML as a decimal integer, so the file
ends up with unexpected permissions. Quote it — `mode: "0644"` — or use symbolic
mode. Mirrors `risky-octal`.

## ANS009 — deprecated sudo / sudo_user (error)

`sudo` and `sudo_user` were removed in favour of the `become` system. Use
`become` and `become_user`.

## ANS010 — become_user without become (error)

`become_user` has no effect unless `become` is enabled, so privilege escalation
silently does not happen. Detected at task scope. Mirrors `partial-become`.

## ANS011 — literal boolean comparison (warning)

`when: var == true` should be written `when: var`. Comparing against a boolean
literal is redundant and error-prone. Mirrors `literal-compare`.

## Suppressing findings

Add an inline `# noqa` comment on the reported line to silence specific rules:

```yaml
- hosts: all  # noqa: ANS005
- shell: /usr/local/bin/migrate  # noqa
```

`# noqa: ANS005,ANS001` suppresses the listed rules; a bare `# noqa` suppresses
every rule on that line. See `docs/configuration.md` for project-level config.
