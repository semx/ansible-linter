"""Domain models for lint reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SEVERITY_RANK: dict[str, int] = {
    "info": 1,
    "warning": 2,
    "error": 3,
}


@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: str
    severity: str
    path: str
    line: int | None
    message: str
    remediation: str
    evidence: str = ""

    @property
    def rank(self) -> int:
        return SEVERITY_RANK[self.severity]

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "path": self.path,
            "line": self.line,
            "message": self.message,
            "remediation": self.remediation,
            "evidence": self.evidence,
        }


@dataclass(frozen=True, slots=True)
class LintReport:
    target: str
    files_checked: int
    findings: tuple[Finding, ...]

    @property
    def highest_severity(self) -> str:
        if not self.findings:
            return "info"
        return max(self.findings, key=lambda finding: finding.rank).severity

    @property
    def counts(self) -> dict[str, int]:
        counts = {"info": 0, "warning": 0, "error": 0}
        for finding in self.findings:
            counts[finding.severity] += 1
        return counts

    def should_fail(self, fail_on: str) -> bool:
        threshold = SEVERITY_RANK[fail_on]
        return any(finding.rank >= threshold for finding in self.findings)

    def as_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "files_checked": self.files_checked,
            "highest_severity": self.highest_severity,
            "counts": self.counts,
            "findings": [finding.as_dict() for finding in self.findings],
        }
