"""Shared helpers for JetPack Python configuration files."""

from __future__ import annotations

from asyncio import sleep
import os
from pathlib import Path
from runpy import run_path
from typing import Any, Dict
from common.config_env import PROJECT_DIRS
from common.command.download_file import FileDownloader
import importlib.util
from common.mbda_icon import MBDA_ICON, print_status_icon
from common.logger import log_fatal, log_warning
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


def download_file_from_url(url: str, destination: str | Path) -> Path:
	"""Telecharge un fichier depuis une URL, avec barre de progression.

	Si le fichier de destination existe deja, le telechargement est ignore.

	Args:
		url: URL du fichier a telecharger (http/https).
		destination: Soit un dossier (le nom du fichier est deduit de l'URL),
			soit un chemin de fichier complet. Le dossier parent est cree
			automatiquement s'il n'existe pas encore.

	Returns:
		Le chemin du fichier telecharge (ou deja present).
	"""
	target_path = Path(destination)

	if target_path.is_dir():
		download_dir, filename = target_path, Path(url.split("?", 1)[0]).name
	else:
		download_dir, filename = target_path.parent, target_path.name

	if not filename:
		raise ValueError(f"Impossible de deduire le nom de fichier depuis l'URL: {url}")

	target_file = download_dir / filename
	if target_file.exists():
		log_warning(f"Le fichier {target_file.name} est deja telecharge, telechargement ignore.")
		return target_file

	return FileDownloader(download_dir=download_dir).download(url, filename=filename)


def extract_tar_file(tar_file_path: str | Path, destination_dir: str | Path, name: str | None = None) -> Path:
	"""
	Extrait une archive dans le dossier indique, avec barre de progression.

	Delegue l'extraction a `FileDownloader.extract`, qui affiche une barre de
	progression (par fichier pour les archives tar/zip, indeterminee pour les
	autres formats geres par patoolib).

	Args:
		tar_file_path: Chemin de l'archive.
		destination_dir: Dossier de destination.
		name: Nom de repertoire (ou fichier) donne a l'extraction. Si fourni,
			l'archive est extraite dans `destination_dir / name` au lieu de
			directement dans `destination_dir`. Par defaut (None), le contenu
			de l'archive est extrait directement dans `destination_dir`.

	Returns:
		Le chemin du dossier de destination.

	Raises:
		FileNotFoundError: Si l'archive n'existe pas.
		RuntimeError: Si l'extraction echoue.
	"""

	if not os.path.isfile(tar_file_path):
		raise FileNotFoundError(f"Archive introuvable : {tar_file_path}")

	destination_dir = Path(destination_dir)
	if name:
		destination_dir = destination_dir / name

	try:
		return FileDownloader(download_dir=destination_dir).extract(tar_file_path, destination_dir)
	except Exception as e:
		raise RuntimeError(f"Erreur lors de l'extraction : {e}") from e


def extract_tar_file_allow_absolute_symlinks(
	tar_file_path: str | Path,
	destination_dir: str | Path,
	name: str | None = None,
) -> Path:
	"""Extrait une archive tar en autorisant les liens absolus (cas rootfs NVIDIA)."""
	if not os.path.isfile(tar_file_path):
		raise FileNotFoundError(f"Archive introuvable : {tar_file_path}")

	destination_dir = Path(destination_dir)
	if name:
		destination_dir = destination_dir / name

	try:
		return FileDownloader(download_dir=destination_dir).extract_tar_allow_absolute_symlinks(
			tar_file_path,
			destination_dir,
		)
	except Exception as e:
		raise RuntimeError(f"Erreur lors de l'extraction : {e}") from e


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
	config_filename = f"{_normalize_version(version_jetpack)}.py"

	if config_filename not in list_config_jetpack:
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
	for key, value in config.items():
		if "url" not in key:
			continue  # Skip keys that are not URLs

		if not value:
			log_fatal(f"No URL provided for {key} in JetPack configuration for version '{version_jetpack}' and board '{board}'.")
			os._exit(1)  # Exit the program with a non-zero status code to indicate an error

		if isinstance(value, dict):
			# Format {"nom_lisible": "url"}, ex: {"Linux_for_Tegra": "https://..."}
			name, url = next(iter(value.items()))
		else:
			name, url = key, value

		filename = url.split("/")[-1]
		destination = Path(PROJECT_DIRS["download"]) / board / version_jetpack / filename
		try:
			downloaded_file = download_file_from_url(url, destination)
		except Exception as e:
			log_fatal(f"Failed to download {key} from {url}: {e}")
			os._exit(1)  # Exit the program with a non-zero status code to indicate an error

		try:
			#extract the downloaded file to the output directory
			# bases name board/version_jetpack
			extract_destination = Path(PROJECT_DIRS["output"]) / board / version_jetpack
			if key == "jetapack_url_sample_rootfs":
				extract_tar_file_allow_absolute_symlinks(downloaded_file, extract_destination, name=name)
			else:
				extract_tar_file(downloaded_file, extract_destination, name=name)

		except Exception as e:
			log_fatal(f"Failed to extract {downloaded_file} to {PROJECT_DIRS['output']}: {e}")
			os._exit(1)  # Exit the program with a non-zero status code to indicate an error
				
def _normalize_version(version: str) -> str:
	normalized = version.strip()
	if normalized.startswith("jetpack-"):
		return normalized
	if normalized.startswith("jetpack."):
		normalized = normalized.removeprefix("jetpack.")
	elif normalized.startswith("jetpack"):
		normalized = normalized.removeprefix("jetpack").lstrip("-._ ")
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
	return jetpack_config_dir(board) / f"{_normalize_version(version)}.py"


def list_available_jetpack_versions(board: str = "jetson-orin-nano") -> list[str]:
	config_dir = jetpack_config_dir(board)
	if not config_dir.exists():
		return []
	versions: list[str] = []
	for path in sorted(config_dir.iterdir()):
		if path.is_file() and path.name.startswith("jetpack-"):
			versions.append(path.stem.removeprefix("jetpack-"))
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


__all__ = [
	"REQUIRED_JETPACK_URL_KEYS",
	"get_list_jetpack",
	"get_config_jetpack",
	"jetpack_config_path",
	"list_available_jetpack_versions",
	"load_jetpack_definition",
	"validate_jetpack_definition",
	"load_and_validate_jetpack_definition",
	"download_file_from_url",
]
