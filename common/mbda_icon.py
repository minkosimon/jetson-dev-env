from rich.columns import Columns
from rich.console import Console
from rich.text import Text

MBDA_ICON = """
⠀⣾⣿⢿⣿⣠⣾⣿⣿⡿⢠⣿⣿⣋⣿⣿⠇⣰⣿⣿⠋⣻⣿⣷⠀⣴⣿⢿⣿⣿
⣼⣿⡟⢸⣿⡿⢣⣿⣿⢁⣿⣿⣯⣽⣿⡿⢣⣿⣿⣧⣴⣿⢯⣵⣾⡿⠛⢻⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡴⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡰⡇⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠠⣤⣄⣠⠶⢒⢟⢴⡄⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⡰⣶⡒⠖⠛⢯⠁⢺⡲⣱⡤⠄⠒⣿⡆⢤⣄⣀⡀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡀⠤⠤⡶⠶⣍⠟⠳⣍⢳⡹⡄⢀⢠⠧⠖⣋⣀⠠⢛⡫⠊⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡀⠤⠐⠂⠈⠉⠒⢄⠀⠀⠀⠀⠀⢠⠀⢹⢀⣇⠟⣾⣿⣿⣿⣬⡡⣶⠃⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⢀⠤⠊⠁⠀⠀⠀⠀⠀⠀⠀⠈⡆⠀⡀⣤⣶⣿⡥⣞⣫⣷⣷⣿⢉⡠⠐⠉⠀⠘⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⢀⡤⠊⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣜⣰⣷⡿⠷⠟⠋⠁⠛⠛⠛⠛⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⢀⠔⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⡴⠛⠋⠁⠀⠀⠀⠐⠀⠂⠀⠀⠂⣁⣀⣀⣀⠀⢀⠀⠀⢀⠀⡀⢀⠀⠀⠰
⠈⢱⣅⣀⡀⠀⠀⠀⠀⠀⠀⢀⣀⡀⠤⠒⠈⠀⠂⠐⠒⠐⠺⠥⠠⢠⢤⠤⠾⠌⠍⠄⠂⠁⠑⠊⠁⠀⠀⡈⠀⠈⡉⠋⠀⠀
⠀⠀⠈⠉⠉⠉⢉⠉⠉⠉⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠂⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠐⠆⠄⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠐⠘⠀⠀⠀⠌⠤⠤⠄⠀⠘⠀⠀⠀⠀⠀⠀⠀
Copyright © MBDA 2026
"""

MBDA_ICON_GCC = """
====================================
    STATUS CROSS-COMPILATION
⢠⣶⡦⠀⣴⣦⠄⣤⣶⡄⠀⠀⠀⠀⢠⣶⡤⢠⣴⣦⠀⢲⡆⠀⣶⠀⣶⣦⡀⣶⠆⣶⠀⠀⣶⣶
⣿⢀⣀⢸⡇⠀⢸⡇⠀⠁⠀⠀⠀⠀⣿⠀⠀⣿⠀⢸⡇⣿⣧⢸⢻⠀⣿⣸⡇⣻⠀⣿⠀⠀⣧⣤
⣷⠘⣿⢸⡇⠀⢸⡇⠀⠀⠀⣶⡆⠀⣿⠀⠀⣿⠀⢸⡇⣿⢹⣸⢸⠀⣷⠟⠁⣿⠀⣿⠀⠀⡟⠛
⢹⣶⣿⠈⣷⣶⠀⢻⣶⡇⠀⠀⠀⠀⢹⣶⡆⠘⣷⣾⠁⣿⢸⡏⢸⠀⣿⠀⠀⣿⡆⣿⣶⡆⣷⣶
====================================
"""

MBDA_ICON_LINUX ="""
 STATUS ENVIRONMENT LINUX DRIVER⠀
⠀⠀⠀⠀⠀⠀⠀⢠⣾⣿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⣿⠟⣿⡟⡛⢿⣿⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⢿⠛⠜⠟⢟⢼⣿⡄⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⣸⢖⡄⡒⠅⠺⣿⣧⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢀⣴⡟⠀⠀⠀⠀⠀⢻⣿⣷⡄⠀⠀⠀
⠀⠀⠀⠀⢀⣾⠟⠀⠀⠀⠀⠀⠀⠀⢻⣿⣿⡄⠀⠀
⠀⠀⠀⠀⣾⡝⠀⠀⠀⠀⠀⠀⠀⠀⠈⣿⢹⣿⡀⠀
⠀⠀⠀⡸⠻⣄⠀⠀⠀⠀⠀⠀⠀⢀⢀⠃⠿⣿⠃⠀
⢠⠐⠊⠀⠀⠈⢷⣤⡀⠀⠀⠀⠀⢸⠀⠃⠊⠀⢁⠀
⢀⠀⠀⠀⠀⠀⠀⠻⣁⡀⠀⣀⣠⡆⠀⠀⠀⠀⠀⡡
⠐⠀⠤⠀⡀⠀⠀⢀⠛⠛⠛⠛⠛⠇⠀⠀⡠⠐⠁⠀
⠀⠀⠀⠀⠀⠉⠀⠁⠀⠀⠀⠀⠀⠀⠉⠁⠀⠀⠀⠀
"""

_icon_console = Console()

_STATUS_ICONS = {
	"linux": MBDA_ICON_LINUX,
	"gcc": MBDA_ICON_GCC,
}


def print_status_icon(icon: str, color: str = "green") -> None:
	"""Affiche une icone MBDA (Linux ou GCC) coloree avec rich.

	Args:
		icon: Icone a afficher : "linux" ou "gcc".
		color: Couleur rich (ex: "red", "green", "cyan", ...).
	"""
	normalized = icon.strip().lower()
	if normalized not in _STATUS_ICONS:
		raise ValueError(f"Icone inconnue: {icon!r}. Valeurs possibles: {list(_STATUS_ICONS)}")

	_icon_console.print(_STATUS_ICONS[normalized], style=color)


def print_status_icons(*icons: tuple[str, str]) -> None:
	"""Affiche plusieurs icones MBDA cote a cote.

	Args:
		*icons: couples (icon, color), ex: ("linux", "green"), ("gcc", "red").
	"""
	renderables = []
	for icon, color in icons:
		normalized = icon.strip().lower()
		if normalized not in _STATUS_ICONS:
			raise ValueError(f"Icone inconnue: {icon!r}. Valeurs possibles: {list(_STATUS_ICONS)}")
		renderables.append(Text(_STATUS_ICONS[normalized].strip("\n"), style=color))

	_icon_console.print(Columns(renderables, padding=(0, 4)))
