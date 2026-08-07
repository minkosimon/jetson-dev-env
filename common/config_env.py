"""Simple project path registry.

This module exposes the main project directories as environment variables.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from common.logger import log_debug, log_info
from common.mbda_icon import print_status_icons


def _project_root() -> Path:
	return Path(__file__).resolve().parent.parent


def _sanitize_key(path_key: str) -> str:
	return path_key.replace("/", "_").replace("-", "_").upper()


PROJECT_ROOT_PATH = _project_root()
PROJECT_DIR_ROOT = str(PROJECT_ROOT_PATH)

# VARIABLE ENVIRONMENT, IMPORTANT: These are the default values for the project environment variables.
PROJECT_ENV_JETSON_STATUS = "NOT_SET"
PROJECT_ENV_JETPACK_VALUE = ""
PROJECT_ENV_GCC_VALUE = ""

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

PROJECT_ENV_VARS = {"PROJECT_DIR_ROOT": PROJECT_DIR_ROOT}
for rel_path, abs_path in PROJECT_DIRS.items():
	if rel_path == ".":
		continue
	PROJECT_ENV_VARS[f"PROJECT_DIR_{_sanitize_key(rel_path)}"] = abs_path


def export_to_environ(overwrite: bool = False) -> None:
	"""Export discovered project path variables to process environment."""
	for name, value in PROJECT_ENV_VARS.items():
		if overwrite or name not in os.environ:
			os.environ[name] = value
			log_debug(f"Exported {name}={value} to environment variables.")

	status_env_gcc = None
	status_env_driver_linux = None
	
	if PROJECT_ENV_GCC_VALUE not in os.environ or PROJECT_ENV_GCC_VALUE == "":
		status_env_gcc = "red"
	elif PROJECT_ENV_GCC_VALUE in os.environ and PROJECT_ENV_GCC_VALUE != "":
		status_env_gcc = "green"

	if PROJECT_ENV_JETPACK_VALUE not in os.environ or PROJECT_ENV_JETPACK_VALUE == "":
		status_env_driver_linux = "red"
	elif PROJECT_ENV_JETPACK_VALUE in os.environ and PROJECT_ENV_JETPACK_VALUE != "":
		status_env_driver_linux = "green"

	print_status_icons(("linux", status_env_driver_linux), ("gcc", status_env_gcc))
			

def unset_from_environ() -> None:
	"""Remove all environment variables created by this module."""
	for name in PROJECT_ENV_VARS:
		os.environ.pop(name, None)
		log_debug(f"Removed {name} from environment variables.")

	log_info("Project path variables removed from environment variables successfully.")


# Export by default when imported.
export_to_environ(overwrite=False)


__all__ = [
	"PROJECT_DIR_ROOT",
	"PROJECT_ROOT_PATH",
	"PROJECT_DIRS",
	"PROJECT_ENV_VARS",
	"export_to_environ",
	"unset_from_environ",
]


if __name__ == "__main__":
	for var_name in sorted(PROJECT_ENV_VARS):
		print(f"{var_name}={PROJECT_ENV_VARS[var_name]}")
