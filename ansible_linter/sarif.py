"""SARIF 2.1.0 rendering for GitHub code scanning."""

from __future__ import annotations

from typing import Any

from ansible_linter import __version__
from ansible_linter.models import LintReport
from ansible_linter.rules import RULES

SARIF_LEVELS = {"info": "note", "warning": "warning", "error": "error"}
INFORMATION_URI = "https://github.com/semx/ansible-linter"


def to_sarif(report: LintReport) -> dict[str, Any]:
    rules = [
        {
            "id": rule.rule_id,
            "name": rule.rule_id,
            "shortDescription": {"text": rule.summary},
            "defaultConfiguration": {"level": SARIF_LEVELS[rule.severity]},
        }
        for rule in RULES
    ]

    results: list[dict[str, Any]] = []
    for finding in report.findings:
        physical: dict[str, Any] = {"artifactLocation": {"uri": finding.path}}
        if finding.line is not None:
            physical["region"] = {"startLine": finding.line}
        results.append(
            {
                "ruleId": finding.rule_id,
                "level": SARIF_LEVELS[finding.severity],
                "message": {"text": finding.message},
                "locations": [{"physicalLocation": physical}],
            }
        )

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ansible-linter",
                        "version": __version__,
                        "informationUri": INFORMATION_URI,
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }
