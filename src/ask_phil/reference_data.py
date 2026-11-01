"""Locate the configured reference registry without depending on caller working directory."""

import os
from pathlib import Path


def reference_directory() -> Path:
    configured = os.environ.get("ASK_PHIL_REFERENCE_DIRECTORY")
    directory: Path | None
    if configured:
        directory = Path(configured)
        if not directory.is_absolute():
            raise ValueError("ASK_PHIL_REFERENCE_DIRECTORY must be an absolute path.")
    else:
        directory = next(
            (
                p / "data" / "references"
                for p in Path(__file__).resolve().parents
                if (p / "pyproject.toml").is_file() and (p / "data" / "references").is_dir()
            ),
            None,
        )
    if directory is None or not directory.is_dir() or not any(directory.glob("*.json")):
        raise ValueError("Reference registry unavailable; configure ASK_PHIL_REFERENCE_DIRECTORY.")
    return directory
