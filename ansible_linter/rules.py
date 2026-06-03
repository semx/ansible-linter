"""Line-oriented Ansible lint rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ansible_linter.models import Finding


TASK_START_RE = re.compile(
    r"^(?P<indent>\s*)-\s*(?:(?:name\s*:)|(?P<module>shell|command|raw|apt|yum|dnf|package|service|debug|set_fact|uri|copy|template)\s*:)"
)
MODULE_RE = re.compile(r"^\s*-?\s*(shell|command|raw|apt|yum|dnf|package|service)\s*:")
HOSTS_ALL_RE = re.compile(r"^\s*-?\s*hosts\s*:\s*(all|['\"]all['\"])\s*(?:#.*)?$", re.IGNORECASE)
ALLOW_HOSTS_ALL = "ansible-linter: allow hosts-all"
SECRET_WORDS = ("password", "passwd", "token", "secret", "api_key", "private_key")
# ansible-lint no-changed-when only accepts these guards (not when/check_mode).
IDEMPOTENCY_HINTS = ("changed_when:", "creates:", "removes:")
PACKAGE_MODULES = ("apt:", "yum:", "dnf:", "package:")
# mode: 0644 / mode: 644 unquoted -> YAML parses as decimal (ansible-lint risky-octal).
MODE_OCTAL_RE = re.compile(r"^\s*mode\s*:\s*(0?\d{3,4})\s*(?:#.*)?$")
# sudo / sudo_user were removed in favour of become (Ansible 2.4+ become system).
SUDO_RE = re.compile(r"^\s*-?\s*sudo(?:_user)?\s*:", re.IGNORECASE)
BECOME_RE = re.compile(r"\bbecome\s*:")
BECOME_USER_RE = re.compile(r"\bbecome_user\s*:")
# when: x == true  ->  ansible-lint literal-compare.
WHEN_LITERAL_RE = re.compile(r"^\s*-?\s*when\s*:.*(?:==|!=)\s*(?:true|false)\b", re.IGNORECASE)
NOQA_RE = re.compile(r"#\s*noqa(?::\s*(?P<codes>[A-Za-z0-9, ]+))?", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class RuleMeta:
    """Static catalogue entry for one rule (used by the CLI and SARIF output)."""

    rule_id: str
    severity: str
    summary: str


RULES: tuple[RuleMeta, ...] = (
    RuleMeta("ANS001", "warning", "Shell-like task without an idempotency guard"),
    RuleMeta("ANS002", "error", "ignore_errors: true without register"),
    RuleMeta("ANS003", "error", "Secret-looking task without no_log: true"),
    RuleMeta("ANS004", "warning", "Package task pinned to state: latest"),
    RuleMeta("ANS005", "warning", "Play targets hosts: all without a limit"),
    RuleMeta("ANS006", "warning", "Handler without a stable name"),
    RuleMeta("ANS007", "warning", "Role missing a standard file"),
    RuleMeta("ANS008", "error", "File mode is an unquoted octal literal"),
    RuleMeta("ANS009", "error", "Deprecated sudo / sudo_user directive"),
    RuleMeta("ANS010", "error", "become_user set without become"),
    RuleMeta("ANS011", "warning", "Conditional compares against a boolean literal"),
)
RULES_BY_ID: dict[str, RuleMeta] = {rule.rule_id: rule for rule in RULES}


@dataclass(frozen=True, slots=True)
class TaskBlock:
    start_line: int
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    @property
    def normalized(self) -> str:
        return self.text.lower()

    @property
    def first_line(self) -> str:
        return self.lines[0].strip() if self.lines else ""


class RuleSet:
    """Evaluate built-in lint rules for one file."""

    def evaluate_file(self, path: Path, content: str) -> tuple[Finding, ...]:
        lines = content.splitlines()
        findings: list[Finding] = []

        findings.extend(self._hosts_all(path, lines))
        findings.extend(self._unquoted_mode(path, lines))
        findings.extend(self._deprecated_sudo(path, lines))
        findings.extend(self._literal_when(path, lines))
        for block in task_blocks(lines):
            findings.extend(self._shell_idempotency(path, block))
            findings.extend(self._ignore_errors(path, block))
            findings.extend(self._secret_no_log(path, block))
            findings.extend(self._package_latest(path, block))
            findings.extend(self._handler_name(path, block))
            findings.extend(self._partial_become(path, block))

        return tuple(findings)

    def evaluate_role(self, role_dir: Path) -> tuple[Finding, ...]:
        findings = []
        expected = (
            ("tasks/main.yml", "ANS007", "Role is missing tasks/main.yml"),
            ("defaults/main.yml", "ANS007", "Role is missing defaults/main.yml"),
            ("meta/main.yml", "ANS007", "Role is missing meta/main.yml"),
        )
        for relative_path, rule_id, message in expected:
            if not (role_dir / relative_path).exists():
                findings.append(
                    Finding(
                        rule_id=rule_id,
                        severity="warning",
                        path=str(role_dir),
                        line=None,
                        message=message,
                        remediation="Add the standard role file or exclude this directory from linting.",
                        evidence=relative_path,
                    )
                )
        return tuple(findings)

    def _shell_idempotency(self, path: Path, block: TaskBlock) -> tuple[Finding, ...]:
        normalized = block.normalized
        if not any(module in normalized for module in ("shell:", "command:", "raw:")):
            return ()
        if any(hint in normalized for hint in IDEMPOTENCY_HINTS):
            return ()
        return (
            Finding(
                rule_id="ANS001",
                severity="warning",
                path=str(path),
                line=block.start_line,
                message="Shell-like task does not define an idempotency guard",
                remediation="Add changed_when, creates, or removes so the task reports changes correctly.",
                evidence=block.first_line,
            ),
        )

    def _ignore_errors(self, path: Path, block: TaskBlock) -> tuple[Finding, ...]:
        # ansible-lint ignore-errors permits ignore_errors when the result is captured.
        if re.search(r"\bregister\s*:", block.normalized):
            return ()
        for offset, line in enumerate(block.lines):
            if re.search(r"\bignore_errors\s*:\s*true\b", line, re.IGNORECASE):
                return (
                    Finding(
                        rule_id="ANS002",
                        severity="error",
                        path=str(path),
                        line=block.start_line + offset,
                        message="Task ignores failures without capturing the result",
                        remediation="Use failed_when, a rescue block, or register the result to inspect it.",
                        evidence=line.strip(),
                    ),
                )
        return ()

    def _secret_no_log(self, path: Path, block: TaskBlock) -> tuple[Finding, ...]:
        normalized = block.normalized
        if not any(word in normalized for word in SECRET_WORDS):
            return ()
        if re.search(r"\bno_log\s*:\s*true\b", normalized):
            return ()
        return (
            Finding(
                rule_id="ANS003",
                severity="error",
                path=str(path),
                line=block.start_line,
                message="Secret-looking task does not enable no_log",
                remediation="Set no_log: true or move secret handling into a protected module path.",
                evidence=block.first_line,
            ),
        )

    def _package_latest(self, path: Path, block: TaskBlock) -> tuple[Finding, ...]:
        normalized = block.normalized
        if not any(module in normalized for module in PACKAGE_MODULES):
            return ()
        for offset, line in enumerate(block.lines):
            if re.search(r"\bstate\s*:\s*latest\b", line, re.IGNORECASE):
                return (
                    Finding(
                        rule_id="ANS004",
                        severity="warning",
                        path=str(path),
                        line=block.start_line + offset,
                        message="Package task uses state: latest",
                        remediation="Pin package versions or use state: present for repeatable runs.",
                        evidence=line.strip(),
                    ),
                )
        return ()

    def _hosts_all(self, path: Path, lines: list[str]) -> tuple[Finding, ...]:
        findings = []
        for index, line in enumerate(lines, start=1):
            if ALLOW_HOSTS_ALL in line:
                continue
            if HOSTS_ALL_RE.match(line):
                nearby = "\n".join(lines[max(0, index - 3) : index + 3]).lower()
                if "serial:" in nearby or "limit:" in nearby:
                    continue
                findings.append(
                    Finding(
                        rule_id="ANS005",
                        severity="warning",
                        path=str(path),
                        line=index,
                        message="Play targets all hosts without a visible limit",
                        remediation="Use a narrower inventory group, serial rollout, or an explicit allow comment.",
                        evidence=line.strip(),
                    )
                )
        return tuple(findings)

    def _handler_name(self, path: Path, block: TaskBlock) -> tuple[Finding, ...]:
        normalized_path = str(path).replace("\\", "/")
        if "/handlers/" not in normalized_path:
            return ()
        if re.match(r"^\s*-\s*name\s*:", block.lines[0], re.IGNORECASE):
            return ()
        if not MODULE_RE.match(block.lines[0]):
            return ()
        return (
            Finding(
                rule_id="ANS006",
                severity="warning",
                path=str(path),
                line=block.start_line,
                message="Handler should have a stable name",
                remediation="Add a clear handler name so notify references remain maintainable.",
                evidence=block.first_line,
            ),
        )

    def _unquoted_mode(self, path: Path, lines: list[str]) -> tuple[Finding, ...]:
        findings = []
        for index, line in enumerate(lines, start=1):
            if MODE_OCTAL_RE.match(line):
                findings.append(
                    Finding(
                        rule_id="ANS008",
                        severity="error",
                        path=str(path),
                        line=index,
                        message="File mode is an unquoted octal literal",
                        remediation='Quote the mode (mode: "0644") so YAML keeps the leading zero.',
                        evidence=line.strip(),
                    )
                )
        return tuple(findings)

    def _deprecated_sudo(self, path: Path, lines: list[str]) -> tuple[Finding, ...]:
        findings = []
        for index, line in enumerate(lines, start=1):
            if SUDO_RE.match(line):
                findings.append(
                    Finding(
                        rule_id="ANS009",
                        severity="error",
                        path=str(path),
                        line=index,
                        message="Deprecated sudo / sudo_user directive",
                        remediation="Use become and become_user, which replaced sudo in Ansible.",
                        evidence=line.strip(),
                    )
                )
        return tuple(findings)

    def _literal_when(self, path: Path, lines: list[str]) -> tuple[Finding, ...]:
        findings = []
        for index, line in enumerate(lines, start=1):
            if WHEN_LITERAL_RE.match(line):
                findings.append(
                    Finding(
                        rule_id="ANS011",
                        severity="warning",
                        path=str(path),
                        line=index,
                        message="Conditional compares against a boolean literal",
                        remediation="Test the variable directly (when: var) instead of comparing to true/false.",
                        evidence=line.strip(),
                    )
                )
        return tuple(findings)

    def _partial_become(self, path: Path, block: TaskBlock) -> tuple[Finding, ...]:
        normalized = block.normalized
        if not BECOME_USER_RE.search(normalized) or BECOME_RE.search(normalized):
            return ()
        return (
            Finding(
                rule_id="ANS010",
                severity="error",
                path=str(path),
                line=block.start_line,
                message="become_user is set without become",
                remediation="Add become: true; become_user has no effect unless become is enabled.",
                evidence=block.first_line,
            ),
        )


def task_blocks(lines: list[str]) -> tuple[TaskBlock, ...]:
    starts: list[int] = []
    for index, line in enumerate(lines):
        if TASK_START_RE.match(line):
            starts.append(index)

    blocks = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        block_lines = tuple(lines[start:end])
        blocks.append(TaskBlock(start_line=start + 1, lines=block_lines))
    return tuple(blocks)


def noqa_directives(lines: list[str]) -> dict[int, set[str] | None]:
    """Map 1-based line numbers to suppressed rule ids (None means suppress all)."""

    directives: dict[int, set[str] | None] = {}
    for index, line in enumerate(lines, start=1):
        match = NOQA_RE.search(line)
        if not match:
            continue
        codes = match.group("codes")
        if codes:
            directives[index] = {code.strip().upper() for code in codes.split(",") if code.strip()}
        else:
            directives[index] = None
    return directives
