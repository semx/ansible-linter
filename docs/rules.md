# Rules

## ANS001

Shell-like tasks should be guarded by `changed_when`, `creates`, `removes`,
`check_mode`, or a clear `when` condition.

## ANS002

`ignore_errors: true` hides automation failures. Prefer `failed_when`, `rescue`,
or explicit handling for expected failures.

## ANS003

Tasks that contain secret-looking words should use `no_log: true`.

## ANS004

Package tasks should avoid `state: latest` because it makes runs depend on
repository state at execution time.

## ANS005

`hosts: all` should be paired with a rollout limit such as `serial`, a narrower
group, or an explicit allow comment.

## ANS006

Handlers should have stable names for reliable `notify` references.

## ANS007

Role directories should include `tasks/main.yml`, `defaults/main.yml`, and
`meta/main.yml`.
