"""Shared helpers for JetPack Python configuration files."""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from runpy import run_path
from typing import Any, Dict
import requests
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from common.config_env import PROJECT_DIRS
import patoolib
import importlib.util
from common.mbda_icon import MBDA_ICON
from common.logger import (
	configure_logger,
	get_logger,
	log_debug,
	log_error,
	log_fatal,
	log_info,
	log_ok,
	log_warning,
)
###########################################################################################################
#  Le fichier config_env.py definit l'ensemble des chemins de base pour le projet et les sous-repertoires.
# l'avantage d'exporter ces variables dans les variables d'environnement de l'OS est que les scripts shell 
# et les autres outils peuvent y acceder facilement.
# 
#/!\ : les variables d'environment ont un nommage normalise :
#  - les chemins de base sont exportes avec le prefixe PROJECT_DIR_ suivi du nom du sous-repertoire, avec les '/' et '-' remplaces par des '_', 
# et le tout en majuscules. 
# Par exemple, le chemin vers le sous-repertoire 'boards/jetson-orin-nano' sera exporte sous le nom PROJECT_DIR_BOARDS_JETSON_ORIN
#############################################################################################################


REQUIRED_JETPACK_URL_KEYS = (
	"jetpack_info_version",
	"jetpack_info_l4t_release",
	"jetpack_url_driver_package",
	"jetapack_url_sample_rootfs",
	"jetpack_url_toolchain"
)


def mbda_logo():
	"""Return the MBDA logo as a string."""
	print(MBDA_ICON)


def load_variable_from_python_file(fichier, nom_variable):
	try:
		spec = importlib.util.spec_from_file_location("module_temp", fichier)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		return getattr(module, nom_variable)
	except Exception as e:
		raise RuntimeError(f"Failed to load variable '{nom_variable}' from file '{fichier}': {e}")


def download_file_from_url(url: str, destination: str | Path):
	"""Download a file from URL to destination with optional SHA256 check."""
	target_path = Path(destination)
	
	try:
		if not target_path.exists():
			raise Exception(
				f"Le dossier {target_path} n'existe pas. veuillez creer le repertoire download a la racine du projet."
			)

		response = requests.get(url, stream=True)
		response.raise_for_status()

		with target_path.open("wb") as fichier:
			for bloc in response.iter_content(chunk_size=8192):
				fichier.write(bloc)

		log_ok(f"Téléchargement terminé : {url} -> {target_path}")
		return target_path

	except requests.RequestException as e:
		raise Exception(f"Erreur pendant le téléchargement : {e} du fichier {url} vers {target_path}")
	

def extract_tar_file(tar_file_path: str | Path, destination_dir: str | Path):
	"""
	Extrait une archive dans le dossier indique.

	Args:
		tar_file_path: Chemin de l'archive.
		destination_dir: Dossier de destination.

	Returns:
		Le chemin du dossier de destination.

	Raises:
		FileNotFoundError: Si l'archive n'existe pas.
		RuntimeError: Si l'extraction echoue.
	"""

	if not os.path.isfile(tar_file_path):
		raise FileNotFoundError(f"Archive introuvable : {tar_file_path}")

	os.makedirs(destination_dir, exist_ok=True)

	try:
		patoolib.extract_archive(
			tar_file_path,
			outdir=destination_dir,
			verbosity=-1
		)
	except Exception as e:
		raise RuntimeError(f"Erreur lors de l'extraction : {e}") from e

	log_ok(f"Extraction terminée : {tar_file_path} -> {destination_dir}")


def getEnvVariable(nameVar: str = "") -> str:
	"""Get the value of an environment variable, or raise an error if not set."""
	try:
		return os.environ[nameVar]
	except KeyError:
		raise RuntimeError(f"Environment variable {nameVar} doesn't exist please check file config_env.py.")

def list_of_available_file_in_dir(dir_path: str | Path) -> list[str]:
	"""List all files in a directory, returning their names as a list of strings."""
	dir_path = Path(dir_path)
	if not dir_path.is_dir():
		raise ValueError(f"{dir_path} is not a valid directory.")
	return [entry.name for entry in dir_path.iterdir() if entry.is_file()]

def list_of_available_dir_in_dir(dir_path: str | Path) -> list[str]:
	"""List all directories in a directory, returning their names as a list of strings."""
	dir_path = Path(dir_path)
	if not dir_path.is_dir():
		raise ValueError(f"{dir_path} is not a valid directory.")
	return [entry.name for entry in dir_path.iterdir() if entry.is_dir()]


def get_list_of_available_board() -> list[str]:
	"""Get a list of available board directories in the PROJECT_DIR_BOARDS."""
	try:
		rel_path = getEnvVariable("PROJECT_DIR_BOARDS")
		if not os.path.exists(rel_path):
			raise RuntimeError(f"folder {rel_path} doesn't exist, please check if folder exists.")
	except RuntimeError as e:
		log_fatal(f"Exception: {e}")
	return list_of_available_dir_in_dir(rel_path)


def is_valid_board(board_name: str) -> bool:
	"""Check if the given board name corresponds to a valid board directory."""
	try:
		available_boards = get_list_of_available_board()
		return board_name in available_boards
	except RuntimeError as e:
		log_fatal(f"Exception: {e}")
		return False

def get_list_jetpack(board: str = "jetson-orin-nano") -> list[str]:
	"""Get a list of available JetPack configuration files for a specific board."""
	try:
		rel_path = getEnvVariable("PROJECT_DIR_BOARDS")
		rel_path = f"{rel_path}/{board}/jetpack"

		#/!\ : on verifie que le chemin existe, sinon on leve une exception pour informer l'utilisateur
		if not os.path.exists(rel_path):
			raise RuntimeError(f"folder {rel_path} doesn't exist, please check if folder exists.")
		
	except RuntimeError as e:
		log_fatal(f"Exception: {e}")
		
	return list_of_available_file_in_dir(rel_path)


def get_config_jetpack(version_jetpack: str, board: str = "jetson-orin-nano") -> Dict:
	"""Get the JetPack configuration for a specific version and board."""

	list_config_jetpack = get_list_jetpack(board)

	if f"jetpack-{version_jetpack}" not in list_config_jetpack:
		raise RuntimeError(f"JetPack version {version_jetpack} not found for board {board}.")

	#/!\ : on verifie que le fichier de configuration existe, sinon on leve une exception pour informer l'utilisateur
	try:
		return load_variable_from_python_file(jetpack_config_path(version_jetpack, board), "JETPACK_DEFINITION")
	except Exception as e:
		log_fatal(f"Failed to load JetPack configuration for version '{version_jetpack}' and board '{board}': {e}")
		os._exit(1)  # Exit the program with a non-zero status code to indicate an error


def download_jetpack(version_jetpack: str, board: str = "jetson-orin-nano") -> None:
	"""Download the JetPack files for a specific version and board."""

	config = get_config_jetpack(version_jetpack, board)

	# Download each required file from the configuration
	for key in config:
		if "url" not in key:
			continue  # Skip keys that are not URLs
		
		url = config.get(key)
		if url:
			filename = url.split("/")[-1]
			destination = Path(PROJECT_DIRS["download"]) / filename
			try:
				download_file_from_url(url, destination)
			except Exception as e:
				log_fatal(f"Failed to download {key} from {url}: {e}")
				os._exit(1)  # Exit the program with a non-zero status code to indicate an error
def _normalize_version(version: str) -> str:
	normalized = version.strip()
	if normalized.startswith("jetpack-"):
		return normalized
	return f"jetpack-{normalized}"


def jetpack_config_dir(board: str = "jetson-orin-nano") -> Path:
	"""Return the jetpack config directory for a given board."""
	try:
		base_board_dir = Path(getEnvVariable("PROJECT_DIR_BOARDS"))
	except RuntimeError as exc:
		log_fatal(f"Exception: {exc}")
		raise

	config_dir = base_board_dir / board / "jetpack"
	if not config_dir.exists():
		raise FileNotFoundError(f"JetPack folder not found: {config_dir}")

	return config_dir


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
	"get_list_jetpack",
	"get_config_jetpack",
	"jetpack_config_path",
	"list_available_jetpack_versions",
	"load_jetpack_definition",
	"validate_jetpack_definition",
	"load_and_validate_jetpack_definition",
	"ensure_parent_dir",
	"compute_sha256",
	"download_file",
]
