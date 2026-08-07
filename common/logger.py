"""Simple logger for terminal and optional file output.

This module provides:
- log types: INFO, WARNING, FATAL, OK
- output destination: terminal, file, or both
- helper functions for quick usage
"""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum
import os
from pathlib import Path
from typing import TextIO

from rich.console import Console
from rich.text import Text


class LogLevel(IntEnum):
	"""Supported log levels."""
	
	DEBUG = 10
	INFO = 20
	WARNING = 30
	ERROR = 40
	FATAL = 50
	OK = 60
	



class Logger:
	"""Small logger that writes messages to terminal and optionally a file."""

	def __init__(
		self,
		output: str = "terminal",
		file_path: str | Path | None = None,
		min_level: LogLevel = LogLevel.INFO,
		verbose: bool = True,
		append: bool = True,
	) -> None:
		self._output = "terminal"
		self._min_level = min_level
		self._verbose = verbose
		self._file_handle: TextIO | None = None
		self._file_path: Path | None = None
		self._console = Console()

		self.configure_output(output=output, file_path=file_path, append=append)

	def set_min_level(self, level: LogLevel | str) -> None:
		"""Update minimum level required to emit a message."""
		self._min_level = self._parse_level(level)

	def set_verbose(self, verbose: bool) -> None:
		"""Enable or disable INFO logs."""
		self._verbose = bool(verbose)

	def set_terminal(self) -> None:
		"""Route logs only to terminal output."""
		self._close_file()
		self._output = "terminal"

	def set_file(self, file_path: str | Path, append: bool = True) -> None:
		"""Route logs only to file output."""
		path = Path(file_path)
		path.parent.mkdir(parents=True, exist_ok=True)
		mode = "a" if append else "w"

		self._close_file()
		self._file_handle = path.open(mode=mode, encoding="utf-8")
		self._file_path = path
		self._output = "file"

	def set_both(self, file_path: str | Path, append: bool = True) -> None:
		"""Route logs to terminal and file output at the same time."""
		path = Path(file_path)
		path.parent.mkdir(parents=True, exist_ok=True)
		mode = "a" if append else "w"

		self._close_file()
		self._file_handle = path.open(mode=mode, encoding="utf-8")
		self._file_path = path
		self._output = "both"

	def configure_output(self, output: str, file_path: str | Path | None = None, append: bool = True) -> None:
		"""Set logger output mode: terminal, file, or both."""
		if output == "terminal":
			self.set_terminal()
			return

		if output == "file":
			if file_path is None:
				raise ValueError("file_path is required when output='file'.")
			self.set_file(file_path=file_path, append=append)
			return

		if output == "both":
			if file_path is None:
				raise ValueError("file_path is required when output='both'.")
			self.set_both(file_path=file_path, append=append)
			return

		raise ValueError("output must be 'terminal', 'file', or 'both'.")

	def close(self) -> None:
		"""Close open file handle if any."""
		self._close_file()

	def info(self, message: str) -> None:
		self._log(LogLevel.INFO, message, label="INFO", color="yellow", respect_verbose=True)

	def warning(self, message: str) -> None:
		self._log(LogLevel.WARNING, message, label="WARNING", color="orange1", respect_verbose=False)

	def error(self, message: str) -> None:
		self._log(LogLevel.ERROR, message, label="ERROR", color="red", respect_verbose=False)

	def ok(self, message: str) -> None:
		self._log(LogLevel.OK, message, label="OK", color="green", respect_verbose=False)

	def fatal(self, message: str) -> None:
		self._log(LogLevel.FATAL, message, label="FATAL", color="red", respect_verbose=False)

	def debug(self, message: str) -> None:
		self._log(LogLevel.DEBUG, message, label="DEBUG", color="blue", respect_verbose=True)

	@staticmethod
	def _parse_level(level: LogLevel | str) -> LogLevel:
		if isinstance(level, LogLevel):
			return level

		normalized = str(level).strip().upper()
		if normalized == "DEBUG":
			return LogLevel.DEBUG
		if normalized == "INFO":
			return LogLevel.INFO
		if normalized == "WARNING":
			return LogLevel.WARNING
		if normalized == "ERROR":
			return LogLevel.ERROR
		if normalized == "FATAL":
			return LogLevel.FATAL

		raise ValueError(f"Unsupported log level: {level}")

	def _log(
		self,
		level: LogLevel,
		message: str,
		label: str,
		color: str,
		respect_verbose: bool,
	) -> None:
		if respect_verbose and level == LogLevel.INFO and not self._verbose:
			return

		if level < self._min_level:
			return

		timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		label_block = self._format_label(label)
		line = f"[{timestamp}] {label_block} {message}"

		if self._output in ("file", "both"):
			if self._file_handle is None:
				raise RuntimeError("Logger file handle is not initialized.")
			self._file_handle.write(line + "\n")
			self._file_handle.flush()

		if self._output in ("terminal", "both"):
			self._print_terminal(timestamp=timestamp, label=label, color=color, message=message)

	def _print_terminal(self, timestamp: str, label: str, color: str, message: str) -> None:
		text = Text(f"[{timestamp}] ")
		text.append(self._format_label(label), style=color)
		text.append(f" {message}")
		self._console.print(text)

	@staticmethod
	def _format_label(label: str) -> str:
		"""Format label with fixed width so all tags use the same spacing."""
		return f"[ {label:^7} ]"

	def _close_file(self) -> None:
		if self._file_handle is not None:
			self._file_handle.close()
			self._file_handle = None
		self._file_path = None
#---------------------------------------------------------------------------------
#                       Shared logger instance and helper functions
#---------------------------------------------------------------------------------

_default_logger = Logger()


def get_logger() -> Logger:
	"""Return the shared logger instance."""
	return _default_logger


def configure_logger(
	output: str = "terminal",
	file_path: str | Path | None = None,
	min_level: LogLevel | str = LogLevel.INFO,
	verbose: bool = True,
	append: bool = True,
) -> Logger:
	"""Configure and return the shared logger instance."""
	logger = get_logger()
	logger.set_min_level(min_level)
	logger.set_verbose(verbose)
	logger.configure_output(output=output, file_path=file_path, append=append)

	return logger


def log_info(message: str) -> None:
	"""Log an INFO message with the shared logger."""
	_default_logger.info(message)


def log_warning(message: str) -> None:
	"""Log a WARNING message with the shared logger."""
	_default_logger.warning(message)


def log_error(message: str) -> None:
	"""Log an ERROR message with the shared logger."""
	_default_logger.error(message)


def log_ok(message: str) -> None:
	"""Log an OK message with the shared logger."""
	_default_logger.ok(message)


def log_debug(message: str) -> None:
	"""Log a DEBUG message with the shared logger."""
	_default_logger.debug(message)

def log_fatal(message: str) -> None:
	"""Log an fatal message with the shared logger."""
	_default_logger.fatal(message)
	os._exit(1)  # Exit the program with a non-zero status code to indicate an error


#---------------------------------------------------------------------------------
#                       Pour tester le logger, execute ce fichier directement.
#                       Il generera un fichier de log dans le repertoire courant.
#---------------------------------------------------------------------------------
def _run_demo() -> None:
	"""Run a local demo that exercises all logger modes and helpers."""
	demo_log_file = Path(__file__).resolve().parent / "logger_demo.log"

	print("\n=== DEMO 1: terminal mode (verbose=True) ===")
	configure_logger(output="terminal", min_level="INFO", verbose=True)
	log_info("Info message in terminal")
	log_warning("Warning message in terminal")
	log_error("Fatal message in terminal")
	log_ok("Ok message in terminal")

	print("\n=== DEMO 2: terminal mode (verbose=False) ===")
	configure_logger(output="terminal", min_level="INFO", verbose=False)
	log_info("This INFO should be hidden")
	log_warning("WARNING is still displayed")
	log_error("FATAL is still displayed")
	log_ok("OK is still displayed")

	print("\n=== DEMO 3: file mode (overwrite) ===")
	configure_logger(
		output="file",
		file_path=demo_log_file,
		min_level="INFO",
		verbose=True,
		append=False,
	)
	log_info("Info message in file")
	log_warning("Warning message in file")
	log_error("Fatal message in file")
	log_ok("Ok message in file")

	print("\n=== DEMO 4: both mode (append) ===")
	configure_logger(
		output="both",
		file_path=demo_log_file,
		min_level="INFO",
		verbose=True,
		append=True,
	)
	logger = get_logger()
	logger.info("Info message in terminal + file")
	logger.warning("Warning message in terminal + file")
	logger.error("Fatal message in terminal + file")
	logger.ok("Ok message in terminal + file")
	logger.close()

	print(f"\nDemo complete. Log file generated: {demo_log_file}")


if __name__ == "__main__":
	_run_demo()
