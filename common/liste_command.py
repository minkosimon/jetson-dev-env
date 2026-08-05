"""Central command registry.

This module builds one Command manager, registers project commands,
and exposes helper functions to execute them.
"""

from __future__ import annotations

from pathlib import Path
from threading import Thread
from typing import Any

from common.command.command import AsyncHandle, Command
from common.common_function import (
	download_jetpack,
	get_config_jetpack,
	get_list_jetpack,
	list_available_jetpack_versions,
	load_and_validate_jetpack_definition,
)


# Explicit registry: one key associated to one Python command function.
PYTHON_COMMANDS: dict[str, Any] = {
	"download_jetpack": download_jetpack,
	"get_list_jetpack": get_list_jetpack,
	"get_config_jetpack": get_config_jetpack,
	"list_available_jetpack_versions": list_available_jetpack_versions,
	"load_and_validate_jetpack_definition": load_and_validate_jetpack_definition,
}


def create_command_manager(workdir: str | Path | None = None, env: dict[str, str] | None = None) -> Command:
	"""Create a Command manager and register all default project commands."""
	manager = Command(workdir=workdir, env=env)

	# Register python commands from the explicit key->function dictionary.
	for key, func in PYTHON_COMMANDS.items():
		manager.register(key, func)

	# Bridges to command execution types handled by Command itself.
	manager.register("bash", lambda command, sync=True, key="bash": manager.run_bash(command, sync=sync, key=key))
	manager.register(
		"script",
		lambda script_path, script_args=None, sync=True, key="script": manager.run_script(
			script_path=script_path,
			script_args=script_args,
			sync=sync,
			key=key,
		),
	)
	manager.register(
		"remote",
		lambda target_ip, remote_command, target_user="nvidia", sync=True, key="remote": manager.run_remote(
			target_ip=target_ip,
			remote_command=remote_command,
			target_user=target_user,
			sync=sync,
			key=key,
		),
	)

	return manager


COMMAND_MANAGER = create_command_manager()


# Full command dictionary used by execute_command for key routing.
COMMAND_FUNCTIONS: dict[str, Any] = {
	**PYTHON_COMMANDS,
	"bash": lambda *args, **kwargs: COMMAND_MANAGER.run_bash(*args, **kwargs),
	"script": lambda *args, **kwargs: COMMAND_MANAGER.run_script(*args, **kwargs),
	"remote": lambda *args, **kwargs: COMMAND_MANAGER.run_remote(*args, **kwargs),
}


def execute_command(command_key: str, *args: Any, async_mode: bool = False, **kwargs: Any) -> Any | Thread:
	"""Execute a registered command by key.

	Set async_mode=True to run Python callable commands in background threads.
	"""
	if command_key not in COMMAND_FUNCTIONS:
		raise KeyError(f"Unknown command key: {command_key}")

	if async_mode:
		return COMMAND_MANAGER.run_async(command_key, *args, **kwargs)
	return COMMAND_MANAGER.run(command_key, *args, **kwargs)


def execute_bash(command: str, sync: bool = True, key: str = "bash") -> int | AsyncHandle:
	"""Convenience wrapper for local bash commands."""
	return COMMAND_MANAGER.run_bash(command=command, sync=sync, key=key)


def execute_script(
	script_path: str | Path,
	script_args: list[str] | None = None,
	sync: bool = True,
	key: str = "script",
) -> int | AsyncHandle:
	"""Convenience wrapper for bash script execution."""
	return COMMAND_MANAGER.run_script(
		script_path=script_path,
		script_args=script_args,
		sync=sync,
		key=key,
	)


def execute_remote(
	target_ip: str,
	remote_command: str,
	target_user: str = "nvidia",
	sync: bool = True,
	key: str = "remote",
) -> int | AsyncHandle:
	"""Convenience wrapper for remote SSH execution."""
	return COMMAND_MANAGER.run_remote(
		target_ip=target_ip,
		remote_command=remote_command,
		target_user=target_user,
		sync=sync,
		key=key,
	)


__all__ = [
	"COMMAND_MANAGER",
	"create_command_manager",
	"execute_command",
	"execute_bash",
	"execute_script",
	"execute_remote",
]
