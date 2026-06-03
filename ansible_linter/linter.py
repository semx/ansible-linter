"""Public linter API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ansible_linter.models import Finding, LintReport
from ansible_linter.rules import RuleSet
from ansible_linter.scanner import collect_yaml_files, discover_role_dirs


@dataclass(frozen=True, slots=True)
class LintConfig:
    include_role_structure: bool = True


class AnsibleLinter:
    """Run built-in rules against files, directories, and roles."""

    def __init__(self, config: LintConfig | None = None, rules: RuleSet | None = None) -> None:
        self.config = config or LintConfig()
        self.rules = rules or RuleSet()

    def lint(self, paths: tuple[str, ...]) -> LintReport:
        files = collect_yaml_files(paths)
        findings: list[Finding] = []

        for path in files:
            content = path.read_text(encoding="utf-8")
            findings.extend(self.rules.evaluate_file(path, content))

        if self.config.include_role_structure:
            for role_dir in discover_role_dirs(paths):
                findings.extend(self.rules.evaluate_role(role_dir))

        findings.sort(key=lambda item: (-item.rank, item.path, item.line or 0, item.rule_id))
        return LintReport(
            target=", ".join(paths),
            files_checked=len(files),
            findings=tuple(findings),
        )

    def lint_text(self, content: str, path: str = "<memory>") -> LintReport:
        findings = self.rules.evaluate_file(Path(path), content)
        sorted_findings = tuple(
            sorted(findings, key=lambda item: (-item.rank, item.path, item.line or 0, item.rule_id))
        )
        return LintReport(target=path, files_checked=1, findings=sorted_findings)
