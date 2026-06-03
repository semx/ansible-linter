"""Public linter API."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

from ansible_linter.models import Finding, LintReport
from ansible_linter.rules import RuleSet, noqa_directives
from ansible_linter.scanner import collect_yaml_files, discover_role_dirs


@dataclass(frozen=True, slots=True)
class LintConfig:
    include_role_structure: bool = True
    select: tuple[str, ...] = field(default_factory=tuple)
    ignore: tuple[str, ...] = field(default_factory=tuple)
    exclude: tuple[str, ...] = field(default_factory=tuple)


def _sort_key(finding: Finding) -> tuple[int, str, int, str]:
    return (-finding.rank, finding.path, finding.line or 0, finding.rule_id)


class AnsibleLinter:
    """Run built-in rules against files, directories, and roles."""

    def __init__(self, config: LintConfig | None = None, rules: RuleSet | None = None) -> None:
        self.config = config or LintConfig()
        self.rules = rules or RuleSet()

    def lint(self, paths: tuple[str, ...]) -> LintReport:
        files = tuple(path for path in collect_yaml_files(paths) if not self._is_excluded(path))
        findings: list[Finding] = []

        for path in files:
            content = path.read_text(encoding="utf-8")
            findings.extend(self._apply_noqa(self.rules.evaluate_file(path, content), content))

        if self.config.include_role_structure:
            for role_dir in discover_role_dirs(paths):
                if self._is_excluded(role_dir):
                    continue
                findings.extend(self.rules.evaluate_role(role_dir))

        selected = sorted(self._select(findings), key=_sort_key)
        return LintReport(
            target=", ".join(paths),
            files_checked=len(files),
            findings=tuple(selected),
        )

    def lint_text(self, content: str, path: str = "<memory>") -> LintReport:
        findings = self._apply_noqa(self.rules.evaluate_file(Path(path), content), content)
        selected = sorted(self._select(findings), key=_sort_key)
        return LintReport(target=path, files_checked=1, findings=tuple(selected))

    def _select(self, findings: tuple[Finding, ...] | list[Finding]) -> list[Finding]:
        result = []
        for finding in findings:
            if self.config.select and finding.rule_id not in self.config.select:
                continue
            if finding.rule_id in self.config.ignore:
                continue
            result.append(finding)
        return result

    def _is_excluded(self, path: Path) -> bool:
        text = str(path)
        return any(fnmatch.fnmatch(text, pattern) for pattern in self.config.exclude)

    @staticmethod
    def _apply_noqa(findings: tuple[Finding, ...], content: str) -> tuple[Finding, ...]:
        directives = noqa_directives(content.splitlines())
        if not directives:
            return findings
        kept = []
        for finding in findings:
            if finding.line is not None and finding.line in directives:
                allowed = directives[finding.line]
                if allowed is None or finding.rule_id in allowed:
                    continue
            kept.append(finding)
        return tuple(kept)
