"""Filesystem scanning helpers."""

from __future__ import annotations

from pathlib import Path


YAML_EXTENSIONS = {".yml", ".yaml"}


def collect_yaml_files(paths: tuple[str, ...]) -> tuple[Path, ...]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_file() and path.suffix.lower() in YAML_EXTENSIONS:
            files.append(path)
        elif path.is_dir():
            files.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file() and candidate.suffix.lower() in YAML_EXTENSIONS
            )

    return tuple(sorted(set(files), key=lambda item: str(item)))


def discover_role_dirs(paths: tuple[str, ...]) -> tuple[Path, ...]:
    role_dirs: set[Path] = set()
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir() and path.name == "roles":
            role_dirs.update(child for child in path.iterdir() if child.is_dir())
        elif path.is_dir() and _looks_like_role(path):
            role_dirs.add(path)
        elif path.is_dir():
            role_dirs.update(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_dir() and _looks_like_role(candidate)
            )
    return tuple(sorted(role_dirs, key=lambda item: str(item)))


def _looks_like_role(path: Path) -> bool:
    return (path / "tasks").is_dir() or (path / "defaults").is_dir() or (path / "meta").is_dir()
