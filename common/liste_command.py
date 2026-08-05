"""Central command registry.

Builds one Command registry and registers every project-level command:
Python functions, bash commands/scripts, and remote (SSH) commands/scripts.
All commands run through the same Command API: run(), run_async(), run_line().
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
	sys.path.insert(0, str(REPO_ROOT))

from common.command.command import Command
from common.common_function import (
	download_jetpack,
	get_config_jetpack,
	get_list_jetpack,
	list_available_jetpack_versions,
	load_and_validate_jetpack_definition,
)
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Python functions available by key.
PYTHON_COMMANDS: dict[str, Any] = {
	"download_jetpack": download_jetpack,
	"get_list_jetpack": get_list_jetpack,
	"get_config_jetpack": get_config_jetpack,
	"list_available_jetpack_versions": list_available_jetpack_versions,
	"load_and_validate_jetpack_definition": load_and_validate_jetpack_definition,
}


def build_registry(workdir: str | Path | None = None, env: dict[str, str] | None = None) -> Command:
	"""Create a Command registry with every project-level command registered."""
	registry = Command(workdir=workdir if workdir is not None else REPO_ROOT, env=env)

	for key, func in PYTHON_COMMANDS.items():
		registry.register(key, func)

	registry.register_script("setup-build-env", SCRIPTS_DIR / "setup-build-env.sh")
	registry.register_bash(
		"setup-env",
		f"source '{SCRIPTS_DIR / 'env-jetpack.sh'}' '{{0}}' "
		"&& env | grep -E '^(JETPACK_VERSION|KERNEL_SRC|CROSS_COMPILE|ARCH)='",
	)

	return registry


# Shared registry used across the project.
COMMANDS = build_registry()


def _example_main() -> None:
	"""Run lightweight examples to illustrate the project command registry."""
	print("=== Registered command keys ===")
	print(COMMANDS.keys())

	print("\n=== Example: run a python command ===")
	versions = COMMANDS.run("list_available_jetpack_versions", board="jetson-orin-nano")
	print(f"Available jetpack versions: {versions}")

	print("\n=== Example: same call via run_line ===")
	versions_via_line = COMMANDS.run_line("list_available_jetpack_versions --board jetson-orin-nano")
	print(f"Available jetpack versions: {versions_via_line}")

	print("\n=== Example: unknown key handling ===")
	try:
		COMMANDS.run("unknown_command")
	except KeyError as exc:
		print(f"Expected error: {exc}")


__all__ = ["Command", "COMMANDS", "PYTHON_COMMANDS", "build_registry", "REPO_ROOT", "SCRIPTS_DIR"]


if __name__ == "__main__":
	_example_main()
