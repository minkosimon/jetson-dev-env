"""Telechargement de fichiers par URL, avec barre de progression et extraction.

Ce module fournit la classe `FileDownloader` qui:
- telecharge un fichier depuis une URL (http/https) en streaming
- peut lancer le telechargement en synchrone (bloquant) ou en arriere-plan
  dans un thread (asynchrone, non bloquant)
- affiche une barre de progression pendant le telechargement (module "rich")
- decompresse automatiquement le fichier telecharge si c'est une archive
  connue (zip, tar, tar.gz, tar.bz2, ...) grace a "patoolib"
"""

from __future__ import annotations

import shutil
import sys
import tarfile
import zipfile
from pathlib import Path
from threading import Thread
from typing import Callable

import patoolib
import requests
from rich.progress import (
	BarColumn,
	DownloadColumn,
	Progress,
	TextColumn,
	TimeElapsedColumn,
	TimeRemainingColumn,
	TransferSpeedColumn,
)

# Permet d'importer "common.logger" meme si ce fichier est execute directement
# (ex: `python dowload_file.py`), et pas seulement importe depuis le package.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
	sys.path.insert(0, str(REPO_ROOT))

from common.logger import log_error, log_info, log_ok, log_warning  # noqa: E402


# Archives basees sur "tar" (module standard tarfile) : progression par nombre de membres.
TAR_EXTENSIONS = (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")

# Archives zip (module standard zipfile) : progression par nombre de membres.
ZIP_EXTENSIONS = (".zip",)

# Autres formats d'archive geres via patoolib (7z, rar, ...) : ce dernier delegue
# a un outil systeme externe, donc seule une barre indeterminee est possible.
OTHER_ARCHIVE_EXTENSIONS = (".7z", ".rar")

# Toutes les extensions reconnues comme archives compressees. Utilisees pour decider
# automatiquement si le fichier telecharge doit etre decompresse.
ARCHIVE_EXTENSIONS = TAR_EXTENSIONS + ZIP_EXTENSIONS + OTHER_ARCHIVE_EXTENSIONS


class DownloadError(Exception):
	"""Erreur levee en cas d'echec de telechargement ou d'extraction."""


class _CountingReader:
	"""Enveloppe un fichier binaire et notifie le nombre d'octets lus.

	Utilise pour piloter une barre de progression pendant un parcours en
	streaming (lecture sequentielle unique), sans jamais parcourir le fichier
	deux fois.
	"""

	def __init__(self, fileobj, on_read: Callable[[int], None]) -> None:
		self._fileobj = fileobj
		self._on_read = on_read

	def read(self, size: int = -1) -> bytes:
		data = self._fileobj.read(size)
		if data:
			self._on_read(len(data))
		return data

	def __getattr__(self, name):
		return getattr(self._fileobj, name)


class FileDownloader:
	"""Gere le telechargement (sync/async) de fichiers par URL, avec barre de
	progression et extraction automatique des archives.

	Exemple d'utilisation:

		downloader = FileDownloader(download_dir="download")

		# Telechargement bloquant, puis extraction automatique dans "output"
		# si le fichier telecharge est une archive connue.
		path = downloader.download(url, extract_dir="output")

		# Telechargement en arriere-plan (thread), sans bloquer le programme.
		thread = downloader.download(url, extract_dir="output", async_mode=True)
		thread.join()  # attendre la fin si necessaire
	"""

	def __init__(self, download_dir: str | Path, chunk_size: int = 8192, timeout: int = 30) -> None:
		"""
		Args:
			download_dir: Dossier ou les fichiers telecharges sont enregistres.
			chunk_size: Taille des blocs lus depuis la reponse HTTP (en octets).
			timeout: Delai maximum (secondes) pour etablir la connexion HTTP.
		"""
		self.download_dir = Path(download_dir)
		self.download_dir.mkdir(parents=True, exist_ok=True)
		self.chunk_size = chunk_size
		self.timeout = timeout

	# ------------------------------------------------------------------
	# API publique
	# ------------------------------------------------------------------

	def download(
		self,
		url: str,
		filename: str | None = None,
		extract_dir: str | Path | None = None,
		async_mode: bool = False,
		on_done: Callable[[Path], None] | None = None,
	) -> Path | Thread:
		"""Telecharge un fichier depuis une URL, avec extraction optionnelle.

		Args:
			url: URL du fichier a telecharger (http/https).
			filename: Nom du fichier local. Par defaut, deduit de l'URL.
			extract_dir: Si fourni et que le fichier telecharge est une archive
				connue, elle est decompressee dans ce dossier apres le telechargement.
			async_mode: Si True, le telechargement s'execute dans un thread separe
				et la methode retourne immediatement le Thread (non bloquant).
				Si False (defaut), la methode bloque jusqu'a la fin et renvoie le chemin.
			on_done: Callback optionnel appele avec le chemin final (fichier ou
				dossier extrait) une fois le telechargement (et l'extraction) termines.
				Utile pour etre notifie quand async_mode=True.

		Returns:
			Le chemin du resultat (mode synchrone) ou le Thread demarre (mode asynchrone).
		"""
		if not url.startswith(("http://", "https://")):
			raise ValueError(f"URL invalide (http/https attendu) : {url}")

		if async_mode:
			thread = Thread(
				target=self._run_download,
				args=(url, filename, extract_dir, on_done),
				daemon=True,
			)
			thread.start()
			return thread

		return self._run_download(url, filename, extract_dir, on_done)

	def is_archive(self, path: str | Path) -> bool:
		"""Indique si le fichier a une extension d'archive reconnue."""
		name = Path(path).name.lower()
		return any(name.endswith(ext) for ext in ARCHIVE_EXTENSIONS)

	def extract(self, archive_path: str | Path, destination_dir: str | Path) -> Path:
		"""Decompresse une archive (zip, tar, tar.gz, tar.bz2, ...) dans un dossier,
		avec une barre de progression.

		Args:
			archive_path: Chemin du fichier archive a decompresser.
			destination_dir: Dossier de destination (cree automatiquement si absent).

		Returns:
			Le dossier de destination.
		"""
		archive_path = Path(archive_path)
		destination_dir = Path(destination_dir)

		if not archive_path.is_file():
			raise FileNotFoundError(f"Archive introuvable : {archive_path}")

		if destination_dir.exists() and any(destination_dir.iterdir()):
			log_warning(f"Le dossier {destination_dir} existe deja et n'est pas vide, extraction ignoree.")
			return destination_dir

		destination_dir.mkdir(parents=True, exist_ok=True)
		name = archive_path.name.lower()

		log_info(f"Extraction : {archive_path.name} -> {destination_dir}")

		try:
			if name.endswith(ZIP_EXTENSIONS):
				self._extract_zip_with_progress(archive_path, destination_dir)
			elif name.endswith(TAR_EXTENSIONS):
				self._extract_tar_with_progress(archive_path, destination_dir)
			else:
				# Formats geres par un outil externe (7z, rar, ...) : patoolib ne fournit
				# pas de progression par fichier, on affiche donc une barre indeterminee
				# (elle "pulse" pendant toute la duree de l'extraction, bloquante).
				self._extract_with_indeterminate_progress(archive_path, destination_dir)
		except Exception as exc:
			raise DownloadError(f"Erreur lors de l'extraction de {archive_path} : {exc}") from exc

		self._flatten_single_top_level_dir(destination_dir)

		log_ok(f"Extraction terminee : {archive_path} -> {destination_dir}")
		return destination_dir

	def extract_tar_allow_absolute_symlinks(self, archive_path: str | Path, destination_dir: str | Path) -> Path:
		"""Extract tar archive while allowing absolute symlink targets.

		Use only for trusted archives (e.g., NVIDIA sample rootfs) that legitimately
		contain absolute symlinks.
		"""
		archive_path = Path(archive_path)
		destination_dir = Path(destination_dir)

		if not archive_path.is_file():
			raise FileNotFoundError(f"Archive introuvable : {archive_path}")

		if destination_dir.exists() and any(destination_dir.iterdir()):
			log_warning(f"Le dossier {destination_dir} existe deja et n'est pas vide, extraction ignoree.")
			return destination_dir

		destination_dir.mkdir(parents=True, exist_ok=True)
		name = archive_path.name.lower()

		if not name.endswith(TAR_EXTENSIONS):
			raise DownloadError(f"Archive tar attendue pour ce mode: {archive_path}")

		log_info(f"Extraction (liens absolus autorises) : {archive_path.name} -> {destination_dir}")
		try:
			self._extract_tar_with_progress(archive_path, destination_dir, allow_absolute_symlinks=True)
		except Exception as exc:
			raise DownloadError(f"Erreur lors de l'extraction de {archive_path} : {exc}") from exc

		self._flatten_single_top_level_dir(destination_dir)

		log_ok(f"Extraction terminee : {archive_path} -> {destination_dir}")
		return destination_dir

	@staticmethod
	def _flatten_single_top_level_dir(destination_dir: Path) -> None:
		"""Remonte le contenu d'un dossier "wrapper" unique a la racine de l'extraction.

		Beaucoup d'archives (ex: x-tools.tbz2, Jetson_Linux_*.tbz2) contiennent
		un seul dossier racine (x-tools/, Linux_for_Tegra/, ...) qui fait double
		emploi avec le nom deja donne au dossier de destination lors de l'appel a
		`extract_tar_file(..., name=...)`. Resultat sans cette etape :
		"Toolchain/x-tools/aarch64-..." ; avec : "Toolchain/aarch64-...".

		Ne fait rien si l'archive contient plusieurs entrees a la racine (ex: un
		rootfs avec bin/, etc/, usr/, ... directement a la racine).
		"""
		entries = list(destination_dir.iterdir())
		if len(entries) != 1 or not entries[0].is_dir():
			return

		wrapper = entries[0]
		for child in list(wrapper.iterdir()):
			shutil.move(str(child), str(destination_dir / child.name))
		wrapper.rmdir()

	@staticmethod
	def _extraction_progress_columns() -> tuple:
		"""Colonnes rich communes aux barres de progression d'extraction (par fichier)."""
		return (
			TextColumn("[bold blue]{task.description}"),
			BarColumn(),
			TextColumn("{task.completed}/{task.total} fichiers"),
			TimeElapsedColumn(),
		)

	def _extract_tar_with_progress(self, archive_path: Path, destination_dir: Path, allow_absolute_symlinks: bool = False) -> None:
		"""Extrait une archive tar (.tar, .tar.gz, .tar.bz2, ...) en un seul passage.

		Pour une archive compressee (gz/bz2/xz), lister prealablement les membres
		via `getmembers()` obligerait a decompresser tout le fichier une premiere
		fois sans aucune progression visible (silence de plusieurs minutes sur une
		grosse archive), puis a le reparcourir pour extraire : on evite ca en
		ouvrant l'archive en mode streaming ("r|*") et en extrayant chaque membre
		au fil de l'eau, avec une progression basee sur les octets compresses lus.
		"""
		total_size = archive_path.stat().st_size
		columns = (
			TextColumn("[bold blue]{task.description}"),
			BarColumn(),
			DownloadColumn(),
			TimeElapsedColumn(),
		)
		with Progress(*columns) as progress:
			task_id = progress.add_task(f"Extract in progress {archive_path.name}", total=total_size)
			with archive_path.open("rb") as raw_file:
				counting_file = _CountingReader(raw_file, lambda n: progress.update(task_id, advance=n))
				with tarfile.open(fileobj=counting_file, mode="r|*") as archive:
					for member in archive:
						# filter="data" est strict (rejette certains liens absolus presents
						# dans des rootfs legitimes). On autorise explicitement ce cas pour
						# des archives de confiance uniquement.
						if allow_absolute_symlinks and (member.issym() or member.islnk()):
							archive.extract(member, path=destination_dir)
						else:
							archive.extract(member, path=destination_dir, filter="data")

	def _extract_zip_with_progress(self, archive_path: Path, destination_dir: Path) -> None:
		"""Extrait une archive zip fichier par fichier."""
		with zipfile.ZipFile(archive_path) as archive:
			names = archive.namelist()
			with Progress(*self._extraction_progress_columns()) as progress:
				task_id = progress.add_task(f"Extract in progress {archive_path.name}", total=len(names))
				for name in names:
					archive.extract(name, path=destination_dir)
					progress.update(task_id, advance=1)

	def _extract_with_indeterminate_progress(self, archive_path: Path, destination_dir: Path) -> None:
		"""Extrait via patoolib (7z, rar, ...) avec une barre indeterminee (pulsante).

		patoolib delegue a un outil systeme externe et ne renvoie aucune progression
		exploitable : la barre "pulse" simplement pendant que l'appel bloquant s'execute.
		"""
		columns = (
			TextColumn("[bold blue]{task.description}"),
			BarColumn(),
			TimeElapsedColumn(),
		)
		with Progress(*columns) as progress:
			progress.add_task(f"Extract in progress {archive_path.name}", total=None)
			patoolib.extract_archive(str(archive_path), outdir=str(destination_dir), verbosity=-1)

	# ------------------------------------------------------------------
	# Implementation interne
	# ------------------------------------------------------------------

	def _run_download(
		self,
		url: str,
		filename: str | None,
		extract_dir: str | Path | None,
		on_done: Callable[[Path], None] | None,
	) -> Path:
		"""Enchaine telechargement puis extraction eventuelle.

		Appelee directement (mode synchrone) ou depuis le thread (mode asynchrone).
		"""
		try:
			file_path = self._download_with_progress(url, filename)

			result_path = file_path
			if extract_dir is not None and self.is_archive(file_path):
				result_path = self.extract(file_path, extract_dir)

			if on_done is not None:
				on_done(result_path)

			return result_path
		except Exception as exc:
			log_error(f"Echec du telechargement de {url} : {exc}")
			raise

	def _download_with_progress(self, url: str, filename: str | None) -> Path:
		"""Telecharge un fichier en streaming, avec une barre de progression."""
		target_name = filename or Path(url.split("?", 1)[0]).name
		if not target_name:
			raise DownloadError(f"Impossible de determiner le nom du fichier depuis l'URL : {url}")
		target_path = self.download_dir / target_name

		response = requests.get(url, stream=True, timeout=self.timeout)
		response.raise_for_status()

		# "Content-Length" peut etre absent (ex: contenu genere dynamiquement).
		# Dans ce cas, la barre de progression bascule automatiquement en mode indetermine.
		content_length = response.headers.get("Content-Length")
		total_size = int(content_length) if content_length else None

		progress_columns = (
			TextColumn("[bold blue]{task.fields[filename]}"),
			BarColumn(),
			DownloadColumn(),
			TransferSpeedColumn(),
			TimeRemainingColumn(),
		)

		with Progress(*progress_columns) as progress:
			task_id = progress.add_task("download", filename=f"download in progress {target_name}", total=total_size)

			with target_path.open("wb") as output_file:
				for chunk in response.iter_content(chunk_size=self.chunk_size):
					if not chunk:
						continue
					output_file.write(chunk)
					progress.update(task_id, advance=len(chunk))

		log_ok(f"Telechargement termine : {url} -> {target_path}")
		return target_path


__all__ = ["FileDownloader", "DownloadError"]


# ---------------------------------------------------------------------------------
#                       Demo / test manuel du module
# ---------------------------------------------------------------------------------

def _run_demo() -> None:
	"""Petit test manuel : telecharge une archive zip et la decompresse."""
	demo_url = "https://github.com/git/git/archive/refs/tags/v2.43.0.zip"
	downloader = FileDownloader(download_dir="download")

	log_info("Telechargement asynchrone (thread) avec extraction automatique...")
	thread = downloader.download(
		demo_url,
		extract_dir="output",
		async_mode=True,
		on_done=lambda path: log_info(f"Termine, resultat dans : {path}"),
	)
	thread.join()


if __name__ == "__main__":
	_run_demo()
