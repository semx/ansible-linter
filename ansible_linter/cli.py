"""Command line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ansible_linter.linter import AnsibleLinter, LintConfig
from ansible_linter.models import SEVERITY_RANK, LintReport


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ansible-linter", description="Static analysis for Ansible")
    subparsers = parser.add_subparsers(dest="command", required=True)

    lint = subparsers.add_parser("lint", help="Lint files or directories")
    lint.add_argument("paths", nargs="+", help="YAML files or directories to scan")
    lint.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    lint.add_argument("--format", choices=("json", "text"), default="json")
    lint.add_argument(
        "--fail-on",
        choices=tuple(SEVERITY_RANK.keys()),
        default="error",
        help="Exit non-zero when a finding meets this severity",
    )
    lint.add_argument(
        "--skip-role-structure",
        action="store_true",
        help="Do not check standard role directory files",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "lint":
        linter = AnsibleLinter(
            config=LintConfig(include_role_structure=not args.skip_role_structure)
        )
        report = linter.lint(tuple(args.paths))
        if args.format == "text":
            print(_text_report(report))
        else:
            print(_json_report(report, pretty=args.pretty))
        return 1 if report.should_fail(args.fail_on) else 0

    parser.error(f"unknown command: {args.command}")
    return 2


def _json_report(report: LintReport, pretty: bool) -> str:
    if pretty:
        return json.dumps(report.as_dict(), indent=2, sort_keys=True)
    return json.dumps(report.as_dict(), sort_keys=True)


def _text_report(report: LintReport) -> str:
    lines = [
        f"target: {report.target}",
        f"files checked: {report.files_checked}",
        f"highest severity: {report.highest_severity}",
    ]
    for finding in report.findings:
        location = finding.path
        if finding.line is not None:
            location = f"{Path(finding.path)}:{finding.line}"
        lines.append(
            f"{finding.severity.upper()} {finding.rule_id} {location} - {finding.message}"
        )
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
