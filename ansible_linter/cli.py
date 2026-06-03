"""Command line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ansible_linter import __version__
from ansible_linter.config import load_file_config
from ansible_linter.linter import AnsibleLinter, LintConfig
from ansible_linter.models import SEVERITY_RANK, LintReport
from ansible_linter.rules import RULES
from ansible_linter.sarif import to_sarif


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ansible-linter", description="Static analysis for Ansible")
    parser.add_argument("--version", action="version", version=f"ansible-linter {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    lint = subparsers.add_parser("lint", help="Lint files or directories")
    lint.add_argument("paths", nargs="+", help="YAML files or directories to scan")
    lint.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    lint.add_argument("--format", choices=("json", "text", "sarif"), default="json")
    lint.add_argument(
        "--fail-on",
        choices=tuple(SEVERITY_RANK.keys()),
        default=None,
        help="Exit non-zero when a finding meets this severity (default: error)",
    )
    lint.add_argument("--select", help="Comma-separated rule ids to run exclusively")
    lint.add_argument("--ignore", help="Comma-separated rule ids to skip")
    lint.add_argument(
        "--exclude",
        action="append",
        help="Glob of file or role paths to skip (may be repeated)",
    )
    lint.add_argument("--config", help="TOML config path (default: .ansible-linter.toml)")
    lint.add_argument(
        "--skip-role-structure",
        action="store_true",
        help="Do not check standard role directory files",
    )

    rules_cmd = subparsers.add_parser("rules", help="List the available rules")
    rules_cmd.add_argument("--format", choices=("text", "json"), default="text")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "rules":
        print(_rules_output(args.format))
        return 0

    if args.command == "lint":
        file_config = load_file_config(args.config)
        select = _codes(args.select) if args.select is not None else _codes(file_config.get("select"))
        ignore = _codes(args.ignore) if args.ignore is not None else _codes(file_config.get("ignore"))
        exclude = tuple(args.exclude) if args.exclude else _strings(file_config.get("exclude"))
        fail_on = args.fail_on or file_config.get("fail_on") or "error"
        if fail_on not in SEVERITY_RANK:
            parser.error(f"invalid fail_on severity: {fail_on}")
        include_roles = not args.skip_role_structure and bool(
            file_config.get("role_structure", True)
        )

        config = LintConfig(
            include_role_structure=include_roles,
            select=select,
            ignore=ignore,
            exclude=exclude,
        )
        report = AnsibleLinter(config=config).lint(tuple(args.paths))

        if args.format == "text":
            print(_text_report(report))
        elif args.format == "sarif":
            print(json.dumps(to_sarif(report), indent=2, sort_keys=True))
        else:
            print(_json_report(report, pretty=args.pretty))
        return 1 if report.should_fail(fail_on) else 0

    parser.error(f"unknown command: {args.command}")
    return 2


def _codes(value: object) -> tuple[str, ...]:
    return tuple(item.upper() for item in _strings(value))


def _strings(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items: list[Any] = value.split(",")
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        items = [value]
    return tuple(str(item).strip() for item in items if str(item).strip())


def _rules_output(fmt: str) -> str:
    if fmt == "json":
        payload: list[dict[str, Any]] = [
            {"id": rule.rule_id, "severity": rule.severity, "summary": rule.summary}
            for rule in RULES
        ]
        return json.dumps(payload, indent=2)
    return "\n".join(f"{rule.rule_id}  {rule.severity:<7}  {rule.summary}" for rule in RULES)


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
