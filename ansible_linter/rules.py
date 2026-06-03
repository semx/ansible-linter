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
HOSTS_ALL_RE = re.compile(r"^\s*-?\s*hosts\s*:\s*(all|['\"]all['\"])\s*$", re.IGNORECASE)
ALLOW_HOSTS_ALL = "ansible-linter: allow hosts-all"
SECRET_WORDS = ("password", "passwd", "token", "secret", "api_key", "private_key")
IDEMPOTENCY_HINTS = ("changed_when:", "creates:", "removes:", "when:", "check_mode:")
PACKAGE_MODULES = ("apt:", "yum:", "dnf:", "package:")


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
        for block in task_blocks(lines):
            findings.extend(self._shell_idempotency(path, block))
            findings.extend(self._ignore_errors(path, block))
            findings.extend(self._secret_no_log(path, block))
            findings.extend(self._package_latest(path, block))
            findings.extend(self._handler_name(path, block))

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
                remediation="Add changed_when, creates, removes, check_mode, or a clear when condition.",
                evidence=block.first_line,
            ),
        )

    def _ignore_errors(self, path: Path, block: TaskBlock) -> tuple[Finding, ...]:
        for offset, line in enumerate(block.lines):
            if re.search(r"\bignore_errors\s*:\s*true\b", line, re.IGNORECASE):
                return (
                    Finding(
                        rule_id="ANS002",
                        severity="error",
                        path=str(path),
                        line=block.start_line + offset,
                        message="Task ignores failures",
                        remediation="Handle expected failures with failed_when or rescue blocks.",
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
