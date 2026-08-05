"""Command execution utilities.

This module provides a Command class that:
- registers callable commands with string keys
- runs commands synchronously or asynchronously
- executes local bash commands
- executes bash scripts
- executes remote commands over SSH
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Thread
from typing import Any, Callable
import os
import subprocess
import sys
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
	sys.path.insert(0, str(REPO_ROOT))

from common.logger import log_debug, log_error, log_info, log_warning


CommandCallable = Callable[..., Any]


@dataclass
class AsyncHandle:
	"""Track a background process and related metadata."""

	key: str
	process: subprocess.Popen[str]
	stdout_thread: Thread | None = None
	stderr_thread: Thread | None = None


class Command:
	"""Register and execute commands by key."""

	def __init__(self, workdir: str | Path | None = None, env: dict[str, str] | None = None) -> None:
		self._workdir = Path(workdir) if workdir is not None else Path.cwd()
		self._env = os.environ.copy()
		if env:
			self._env.update(env)

		self._registry: dict[str, CommandCallable] = {}
		self._async_handles: dict[str, AsyncHandle] = {}

	def register(self, key: str, func: CommandCallable) -> None:
		"""Register a callable command under a unique key."""
		if not key:
			raise ValueError("Command key cannot be empty.")
		if not callable(func):
			raise TypeError("func must be callable.")
		if key in self._registry:
			raise ValueError(f"Command '{key}' is already registered.")

		self._registry[key] = func
		log_debug(f"Command registered: {key}")

	def unregister(self, key: str) -> None:
		"""Remove a previously registered command key."""
		if key in self._registry:
			del self._registry[key]
			log_debug(f"Command unregistered: {key}")

	def keys(self) -> list[str]:
		"""Return sorted list of registered command keys."""
		return sorted(self._registry.keys())

	def run(self, key: str, *args: Any, **kwargs: Any) -> Any:
		"""Run a registered Python callable synchronously."""
		func = self._registry.get(key)
		if func is None:
			raise KeyError(f"Unknown command key: {key}")

		log_info(f"Run command '{key}' (sync)")
		try:
			result = func(*args, **kwargs)
			log_info(f"Command '{key}' completed")
			return result
		except Exception as exc:  # noqa: BLE001
			log_error(f"Command '{key}' failed: {exc}")
			raise

	def run_async(self, key: str, *args: Any, **kwargs: Any) -> Thread:
		"""Run a registered Python callable in a background thread."""
		func = self._registry.get(key)
		if func is None:
			raise KeyError(f"Unknown command key: {key}")

		def _runner() -> None:
			log_info(f"Run command '{key}' (async)")
			try:
				func(*args, **kwargs)
				log_info(f"Command '{key}' completed")
			except Exception as exc:  # noqa: BLE001
				log_error(f"Command '{key}' failed: {exc}")

		thread = Thread(target=_runner, name=f"cmd-{key}", daemon=True)
		thread.start()
		return thread

	def run_bash(self, command: str, sync: bool = True, key: str = "bash") -> int | AsyncHandle:
		"""Execute a local bash command."""
		if not command.strip():
			raise ValueError("Bash command cannot be empty.")

		if sync:
			log_info(f"Run bash (sync): {command}")
			completed = subprocess.run(
				["bash", "-lc", command],
				cwd=str(self._workdir),
				env=self._env,
				text=True,
				capture_output=True,
			)
			self._log_process_output(completed.stdout, completed.stderr)
			if completed.returncode != 0:
				log_error(f"Bash command failed with code {completed.returncode}")
			else:
				log_info("Bash command completed")
			return completed.returncode

		log_info(f"Run bash (async): {command}")
		process = subprocess.Popen(
			["bash", "-lc", command],
			cwd=str(self._workdir),
			env=self._env,
			text=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
		)
		handle = AsyncHandle(key=key, process=process)
		handle.stdout_thread = self._start_stream_thread(process.stdout, "info")
		handle.stderr_thread = self._start_stream_thread(process.stderr, "error")
		self._async_handles[key] = handle
		return handle

	def run_script(
		self,
		script_path: str | Path,
		script_args: list[str] | None = None,
		sync: bool = True,
		key: str = "script",
	) -> int | AsyncHandle:
		"""Execute a bash script file."""
		script = Path(script_path)
		if not script.is_absolute():
			script = self._workdir / script
		if not script.is_file():
			raise FileNotFoundError(f"Script not found: {script}")

		args = script_args if script_args else []
		command = " ".join([f"'{str(script)}'", *[f"'{item}'" for item in args]])
		return self.run_bash(f"bash {command}", sync=sync, key=key)

	def run_remote(
		self,
		target_ip: str,
		remote_command: str,
		target_user: str = "nvidia",
		sync: bool = True,
		key: str = "remote",
	) -> int | AsyncHandle:
		"""Execute a command on a remote target via SSH."""
		if not target_ip.strip():
			raise ValueError("target_ip cannot be empty.")
		if not remote_command.strip():
			raise ValueError("remote_command cannot be empty.")

		ssh_target = f"{target_user}@{target_ip}"
		command = f"ssh {ssh_target} \"{remote_command}\""
		return self.run_bash(command, sync=sync, key=key)

	def poll_async(self, key: str) -> int | None:
		"""Return process return code if finished, else None."""
		handle = self._async_handles.get(key)
		if handle is None:
			raise KeyError(f"Unknown async handle key: {key}")
		return handle.process.poll()

	def wait_async(self, key: str) -> int:
		"""Wait for a background process and return its exit code."""
		handle = self._async_handles.get(key)
		if handle is None:
			raise KeyError(f"Unknown async handle key: {key}")

		code = handle.process.wait()
		if handle.stdout_thread:
			handle.stdout_thread.join(timeout=0.5)
		if handle.stderr_thread:
			handle.stderr_thread.join(timeout=0.5)

		if code == 0:
			log_info(f"Async command '{key}' completed")
		else:
			log_error(f"Async command '{key}' failed with code {code}")
		return code

	def _start_stream_thread(self, stream: Any, level: str) -> Thread | None:
		if stream is None:
			return None

		def _reader() -> None:
			for line in iter(stream.readline, ""):
				clean = line.strip()
				if not clean:
					continue
				if level == "error":
					log_warning(clean)
				else:
					log_info(clean)

		thread = Thread(target=_reader, daemon=True)
		thread.start()
		return thread

	@staticmethod
	def _log_process_output(stdout: str | None, stderr: str | None) -> None:
		if stdout:
			for line in stdout.splitlines():
				if line.strip():
					log_info(line)
		if stderr:
			for line in stderr.splitlines():
				if line.strip():
					log_warning(line)


__all__ = ["Command", "AsyncHandle", "CommandCallable"]

## Demo functions for testing the Command class

def _demo_add(a: int, b: int) -> int:
	return a + b


def _demo_echo(message: str) -> None:
	log_info(f"demo echo: {message}")


def _run_demo() -> int:
	"""Exercise the most useful Command APIs from a single entry point."""
	log_info("=== Command demo start ===")
	manager = Command(workdir=Path.cwd())

	# 1) Register and run Python callables.
	manager.register("add", _demo_add)
	manager.register("echo", _demo_echo)
	result = manager.run("add", 2, 3)
	log_info(f"add result = {result}")
	thread = manager.run_async("echo", "hello from async callable")
	thread.join(timeout=2)

	# 2) Run local bash sync + async.
	bash_rc = manager.run_bash("echo 'hello from sync bash'", sync=True, key="bash-sync")
	log_info(f"sync bash return code = {bash_rc}")
	manager.run_bash("echo 'hello from async bash'", sync=False, key="bash-async")
	async_rc = manager.wait_async("bash-async")
	log_info(f"async bash return code = {async_rc}")

	# 3) Run a generated bash script.
	with tempfile.TemporaryDirectory(prefix="cmd-demo-") as tmp_dir:
		script_path = Path(tmp_dir) / "demo_script.sh"
		script_path.write_text("#!/usr/bin/env bash\necho script:$1\n", encoding="utf-8")
		script_path.chmod(0o755)
		script_rc = manager.run_script(script_path, script_args=["ok"], sync=True, key="script-sync")
		log_info(f"script return code = {script_rc}")

	# 4) Optional remote test if environment variables are provided.
	remote_ip = os.environ.get("COMMAND_DEMO_REMOTE_IP", "").strip()
	if remote_ip:
		remote_user = os.environ.get("COMMAND_DEMO_REMOTE_USER", "nvidia")
		remote_cmd = os.environ.get("COMMAND_DEMO_REMOTE_CMD", "echo remote-ok")
		try:
			remote_rc = manager.run_remote(
				target_ip=remote_ip,
				remote_command=remote_cmd,
				target_user=remote_user,
				sync=True,
				key="remote-sync",
			)
			log_info(f"remote return code = {remote_rc}")
		except Exception as exc:  # noqa: BLE001
			log_warning(f"remote demo skipped/failed: {exc}")
	else:
		log_warning(
			"remote demo skipped (set COMMAND_DEMO_REMOTE_IP to enable remote command test)"
		)

	log_info("=== Command demo end ===")
	return 0


if __name__ == "__main__":
	raise SystemExit(_run_demo())
