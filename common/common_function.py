"""Shared helpers for JetPack Python configuration files."""

from __future__ import annotations

from asyncio import sleep
import os
import subprocess
from pathlib import Path
from runpy import run_path
from typing import Any, Dict
import common.config_env as config_env
from common.config_env import PROJECT_DIRS
from common.command.download_file import FileDownloader
import importlib.util
from common.mbda_icon import MBDA_ICON, print_status_icons
from common.logger import log_error, log_fatal, log_ok, log_warning
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


def _resolve_jetpack_entry(key: str, value: str | dict) -> tuple[str, str]:
	"""Retourne (nom_de_dossier, url) pour une entree de configuration JetPack.

	Format attendu pour `value` : soit une URL (str) -> le nom de dossier est la
	cle elle-meme, soit {"nom_dossier": "url"} (ex: {"Linux_for_Tegra": "https://..."}).
	"""
	if isinstance(value, dict):
		return next(iter(value.items()))
	return key, value


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

		name, url = _resolve_jetpack_entry(key, value)

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


def is_all_folders_available_for_jetson_env(version_jetpack: str, board: str = "jetson-orin-nano") -> bool:
	"""Verifie que tous les dossiers requis (Toolchain, Linux_for_Tegra, Sample_rootfs, ...)
	sont bien presents et non vides dans output/<board>/<version>/.

	Erreur fatale (log_fatal quitte le programme) si un dossier requis est absent ou vide.
	"""
	config = get_config_jetpack(version_jetpack, board)
	output_dir = Path(PROJECT_DIRS["output"]) / board / version_jetpack

	missing = []
	for key, value in config.items():
		if "url" not in key or not value:
			continue
		name, _ = _resolve_jetpack_entry(key, value)
		folder = output_dir / name
		if not folder.is_dir() or not any(folder.iterdir()):
			missing.append(name)

	if missing:
		log_fatal(f"Dossiers requis manquants dans {output_dir} : {', '.join(missing)}")
		return False  # inatteignable (log_fatal quitte le programme), garde pour la lisibilite

	log_ok(f"Tous les dossiers requis sont disponibles dans {output_dir}.")
	return True


def update_env_variable_jetpack(version_jetpack: str, board: str = "jetson-orin-nano") -> None:
	"""Exporte les variables JETPACK_<COMPOSANT> (chemins des composants telecharges)
	et reinitialise l'etat de compilation avant une nouvelle verification.
	"""
	config = get_config_jetpack(version_jetpack, board)
	output_dir = Path(PROJECT_DIRS["output"]) / board / version_jetpack

	for key, value in config.items():
		if "url" not in key or not value:
			continue
		name, _ = _resolve_jetpack_entry(key, value)
		os.environ[f"JETPACK_{key.upper()}"] = str(output_dir / name)

	config_env.PROJECT_ENV_JETSON_STATUS = "DOWNLOADED"
	config_env.PROJECT_ENV_JETPACK_VALUE = ""
	config_env.PROJECT_ENV_GCC_VALUE = ""
	os.environ["PROJECT_ENV_JETSON_STATUS"] = config_env.PROJECT_ENV_JETSON_STATUS

	print_status_icons(("linux", "red"), ("gcc", "red"))


def _compile_helloworld_app(cross_compile: str, app_output_dir: Path) -> bool:
	"""Compile l'application de test helloworld avec le toolchain croise."""
	app_dir = Path(PROJECT_DIRS["custom-application"]) / "helloworld"
	try:
		subprocess.run(
			["make", "-C", str(app_dir), f"CROSS_COMPILE={cross_compile}", f"OUTPUT_DIR={app_output_dir}"],
			check=True,
			capture_output=True,
			text=True,
		)
	except (subprocess.CalledProcessError, FileNotFoundError) as exc:
		log_error(f"Echec de la compilation de l'application helloworld : {exc}")
		return False

	log_ok(f"Application helloworld compilee : {app_output_dir}/helloworld_app")
	return True


def _compile_helloworld_driver(cross_compile: str, kernel_src: Path, driver_output_dir: Path) -> bool:
	"""Compile le module noyau de test helloworld avec le toolchain croise."""
	if not (kernel_src / "Makefile").is_file():
		log_error(f"Sources noyau introuvables pour la compilation du driver : {kernel_src}")
		return False

	driver_dir = Path(PROJECT_DIRS["custom-driver"]) / "helloworld"
	try:
		subprocess.run(
			[
				"make", "-C", str(driver_dir), "modules",
				f"KERNEL_SRC={kernel_src}",
				"ARCH=arm64",
				f"CROSS_COMPILE={cross_compile}",
				f"OUTPUT_DIR={driver_output_dir}",
			],
			check=True,
			capture_output=True,
			text=True,
		)
	except (subprocess.CalledProcessError, FileNotFoundError) as exc:
		log_error(f"Echec de la compilation du driver helloworld : {exc}")
		return False

	log_ok(f"Driver helloworld compile : {driver_output_dir}/helloworld_drv.ko")
	return True


def check_compilation_env(version_jetpack: str, board: str = "jetson-orin-nano") -> None:
	"""Compile l'application et le driver helloworld avec le toolchain JetPack
	telecharge, pour valider la chaine de compilation croisee. Met a jour la
	couleur des icones gcc (application) et linux/driver (module noyau) selon
	le resultat.
	"""
	config = get_config_jetpack(version_jetpack, board)
	output_dir = Path(PROJECT_DIRS["output"]) / board / version_jetpack

	toolchain_name, _ = _resolve_jetpack_entry("jetpack_url_toolchain", config["jetpack_url_toolchain"])
	driver_pkg_name, _ = _resolve_jetpack_entry("jetpack_url_driver_package", config["jetpack_url_driver_package"])

	cross_compile = output_dir / toolchain_name / "aarch64-none-linux-gnu" / "bin" / "aarch64-none-linux-gnu-"
	kernel_src = output_dir / driver_pkg_name / "source" / "kernel"

	app_ok = _compile_helloworld_app(str(cross_compile), output_dir / "app")
	config_env.PROJECT_ENV_GCC_VALUE = str(cross_compile) if app_ok else ""

	driver_ok = _compile_helloworld_driver(str(cross_compile), kernel_src, output_dir / "driver")
	config_env.PROJECT_ENV_JETPACK_VALUE = version_jetpack if driver_ok else ""

	config_env.PROJECT_ENV_JETSON_STATUS = "COMPILED" if (app_ok and driver_ok) else "COMPILE_FAILED"
	os.environ["PROJECT_ENV_JETSON_STATUS"] = config_env.PROJECT_ENV_JETSON_STATUS

	print_status_icons(
		("linux", "green" if driver_ok else "red"),
		("gcc", "green" if app_ok else "red"),
	)


def setup_jetpack_environment(version_jetpack: str, board: str = "jetson-orin-nano") -> None:
	"""Pipeline complet de mise en place de l'environnement JetPack :
	telecharge les composants, verifie que tous les dossiers requis sont
	disponibles, met a jour les variables d'environnement, puis compile
	l'application et le driver de test pour valider la chaine de compilation.
	"""
	download_jetpack(version_jetpack, board)
	is_all_folders_available_for_jetson_env(version_jetpack, board)
	update_env_variable_jetpack(version_jetpack, board)
	check_compilation_env(version_jetpack, board)


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
	"download_jetpack",
	"is_all_folders_available_for_jetson_env",
	"update_env_variable_jetpack",
	"check_compilation_env",
	"setup_jetpack_environment",
]
