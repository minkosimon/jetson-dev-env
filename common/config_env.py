"""Simple project path registry.

This module exposes the main project directories as environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path


def _project_root() -> Path:
	return Path(__file__).resolve().parent.parent


def _sanitize_key(path_key: str) -> str:
	return path_key.replace("/", "_").replace("-", "_").upper()


PROJECT_ROOT_PATH = _project_root()
PROJECT_ROOT = str(PROJECT_ROOT_PATH)

# Keep this list explicit and easy to read.
PROJECT_DIRS = {
	".": str(PROJECT_ROOT_PATH),
	"boards": str(PROJECT_ROOT_PATH / "boards"),
	"boards/jetson-orin-nano": str(PROJECT_ROOT_PATH / "boards" / "jetson-orin-nano"),
	"boards/jetson-orin-nano/jetpack": str(
		PROJECT_ROOT_PATH / "boards" / "jetson-orin-nano" / "jetpack"
	),
	"common": str(PROJECT_ROOT_PATH / "common"),
	"custom-application": str(PROJECT_ROOT_PATH / "custom-application"),
	"custom-driver": str(PROJECT_ROOT_PATH / "custom-driver"),
	"download": str(PROJECT_ROOT_PATH / "download"),
	"output": str(PROJECT_ROOT_PATH / "output"),
	"scripts": str(PROJECT_ROOT_PATH / "scripts"),
}

PROJECT_ENV_VARS = {"PROJECT_ROOT": PROJECT_ROOT}
for rel_path, abs_path in PROJECT_DIRS.items():
	if rel_path == ".":
		continue
	PROJECT_ENV_VARS[f"PROJECT_DIR_{_sanitize_key(rel_path)}"] = abs_path


def export_to_environ(overwrite: bool = False) -> None:
	"""Export discovered project path variables to process environment."""
	for name, value in PROJECT_ENV_VARS.items():
		if overwrite or name not in os.environ:
			os.environ[name] = value


# Export by default when imported.
export_to_environ(overwrite=False)


__all__ = [
	"PROJECT_ROOT",
	"PROJECT_ROOT_PATH",
	"PROJECT_DIRS",
	"PROJECT_ENV_VARS",
	"export_to_environ",
]


if __name__ == "__main__":
	for var_name in sorted(PROJECT_ENV_VARS):
		print(f"{var_name}={PROJECT_ENV_VARS[var_name]}")
