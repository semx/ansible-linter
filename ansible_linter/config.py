"""TOML configuration loading for the linter."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_NAME = ".ansible-linter.toml"


def load_file_config(path: str | Path | None) -> dict[str, Any]:
    """Load linter settings from a TOML file.

    With no path, an optional ``.ansible-linter.toml`` in the working directory is
    used. Settings live under a top-level ``[ansible_linter]`` table or, for
    pyproject-style files, under ``[tool.ansible_linter]``.
    """

    if path is not None:
        target = Path(path)
        if not target.exists():
            raise FileNotFoundError(f"config file not found: {target}")
    else:
        target = Path(DEFAULT_CONFIG_NAME)
        if not target.exists():
            return {}

    with target.open("rb") as handle:
        data: dict[str, Any] = tomllib.load(handle)

    section = data.get("ansible_linter")
    if isinstance(section, dict):
        result: dict[str, Any] = section
        return result

    tool = data.get("tool")
    if isinstance(tool, dict) and isinstance(tool.get("ansible_linter"), dict):
        nested: dict[str, Any] = tool["ansible_linter"]
        return nested

    return {}
