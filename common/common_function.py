"""Shared helpers for JetPack Python configuration files."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from runpy import run_path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from common.config_env import PROJECT_DIRS, PROJECT_ROOT_PATH


REQUIRED_JETPACK_URL_KEYS = (
	"driver_package_url",
	"sample_rootfs_url",
	"public_sources_url",
	"toolchain_url",
)


def project_root() -> Path:
	return PROJECT_ROOT_PATH


def jetpack_config_dir(board: str = "jetson-orin-nano") -> Path:
	rel_path = f"boards/{board}/jetpack"
	if rel_path in PROJECT_DIRS:
		return Path(PROJECT_DIRS[rel_path])
	return project_root() / "boards" / board / "jetpack"


def _normalize_version(version: str) -> str:
	normalized = version.strip()
	if normalized.startswith("jetpack-"):
		return normalized
	return f"jetpack-{normalized}"


def jetpack_config_path(version: str, board: str = "jetson-orin-nano") -> Path:
	return jetpack_config_dir(board) / _normalize_version(version)


def list_available_jetpack_versions(board: str = "jetson-orin-nano") -> list[str]:
	config_dir = jetpack_config_dir(board)
	if not config_dir.exists():
		return []
	versions: list[str] = []
	for path in sorted(config_dir.iterdir()):
		if path.is_file() and path.name.startswith("jetpack-"):
			versions.append(path.name.removeprefix("jetpack-"))
	return versions


def load_jetpack_definition(version: str, board: str = "jetson-orin-nano") -> dict[str, str]:
	config_file = jetpack_config_path(version, board)
	if not config_file.is_file():
		raise FileNotFoundError(f"JetPack config not found: {config_file}")

	namespace = run_path(str(config_file))
	definition = namespace.get("JETPACK_DEFINITION")

	if not isinstance(definition, dict):
		raise ValueError(
			f"JETPACK_DEFINITION must be a dict in {config_file}, got {type(definition).__name__}."
		)

	normalized: dict[str, str] = {}
	for key, value in definition.items():
		if not isinstance(key, str):
			raise ValueError(f"Invalid key type in {config_file}: {type(key).__name__}")
		if not isinstance(value, str):
			raise ValueError(f"Invalid value type for key '{key}' in {config_file}: {type(value).__name__}")
		normalized[key] = value

	return normalized


def validate_jetpack_definition(definition: dict[str, Any]) -> list[str]:
	errors: list[str] = []
	for key in REQUIRED_JETPACK_URL_KEYS:
		value = definition.get(key)
		if not isinstance(value, str) or not value:
			errors.append(f"Missing or empty required key: {key}")
			continue
		if not value.startswith(("http://", "https://")):
			errors.append(f"Invalid URL for key {key}: {value}")
	return errors


def load_and_validate_jetpack_definition(version: str, board: str = "jetson-orin-nano") -> dict[str, str]:
	definition = load_jetpack_definition(version=version, board=board)
	errors = validate_jetpack_definition(definition)
	if errors:
		raise ValueError("JetPack definition validation failed: " + "; ".join(errors))
	return definition


def ensure_parent_dir(path: str | Path) -> Path:
	"""Ensure the destination parent directory exists and return Path."""
	destination = Path(path)
	destination.parent.mkdir(parents=True, exist_ok=True)
	return destination


def compute_sha256(file_path: str | Path, chunk_size: int = 1024 * 1024) -> str:
	"""Compute SHA256 digest for a local file."""
	hash_obj = hashlib.sha256()
	with Path(file_path).open("rb") as stream:
		for chunk in iter(lambda: stream.read(chunk_size), b""):
			hash_obj.update(chunk)
	return hash_obj.hexdigest()


def download_file(
	url: str,
	destination: str | Path,
	*,
	timeout: int = 120,
	overwrite: bool = False,
	user_agent: str = "jetson-dev-env/1.0",
	expected_sha256: str | None = None,
) -> Path:
	"""Download a file from URL to destination with optional SHA256 check."""
	if not url.startswith(("http://", "https://")):
		raise ValueError(f"URL invalide: {url}")

	target_path = ensure_parent_dir(destination)
	if target_path.exists() and not overwrite:
		if expected_sha256:
			current = compute_sha256(target_path)
			if current.lower() != expected_sha256.lower():
				raise ValueError(
					f"Le fichier existe mais le SHA256 ne correspond pas pour {target_path}."
				)
		return target_path

	request = Request(url, headers={"User-Agent": user_agent})
	temp_path = target_path.with_suffix(target_path.suffix + ".part")

	try:
		with urlopen(request, timeout=timeout) as response, temp_path.open("wb") as output:
			shutil.copyfileobj(response, output)
	except HTTPError as exc:
		raise RuntimeError(f"Erreur HTTP pendant le telechargement ({exc.code}): {url}") from exc
	except URLError as exc:
		raise RuntimeError(f"Erreur reseau pendant le telechargement: {url}") from exc

	temp_path.replace(target_path)

	if expected_sha256:
		digest = compute_sha256(target_path)
		if digest.lower() != expected_sha256.lower():
			target_path.unlink(missing_ok=True)
			raise ValueError(
				f"SHA256 invalide pour {target_path}. attendu={expected_sha256} obtenu={digest}"
			)

	return target_path


__all__ = [
	"REQUIRED_JETPACK_URL_KEYS",
	"project_root",
	"jetpack_config_dir",
	"jetpack_config_path",
	"list_available_jetpack_versions",
	"load_jetpack_definition",
	"validate_jetpack_definition",
	"load_and_validate_jetpack_definition",
	"ensure_parent_dir",
	"compute_sha256",
	"download_file",
]
