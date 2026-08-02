#!/usr/bin/env bash
# A sourcer (pas exécuter) : `source scripts/env-jetpack.sh <jetpack_version>`
# Fixe JETPACK_VERSION, KERNEL_SRC, CROSS_COMPILE, ARCH dans le shell courant, en lisant
# configs/jetpack-<version>.mk (la même config que celle utilisée par le Makefile), pour les
# outils annexes qui n'appellent pas make directement (clangd, gdb-multiarch, IDE...).

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
	echo "Ce script doit être sourcé : source scripts/env-jetpack.sh <jetpack_version>" >&2
	exit 1
fi

_ej_version=${1:?usage: source scripts/env-jetpack.sh <jetpack_version>}
_ej_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_ej_cfg="${_ej_root}/configs/jetpack-${_ej_version}.mk"
_ej_probe="${_ej_root}/scripts/.env-jetpack-probe.mk"

if [ ! -f "${_ej_cfg}" ]; then
	echo "Config introuvable : ${_ej_cfg}" >&2
	return 1 2>/dev/null || exit 1
fi

printf 'print-%%:\n\t@echo $($*)\n' > "${_ej_probe}"

_ej_val() { make -s -f "${_ej_cfg}" -f "${_ej_probe}" "print-$1"; }

export JETPACK_VERSION="${_ej_version}"
export KERNEL_SRC=$(_ej_val KERNEL_SRC)
export CROSS_COMPILE=$(_ej_val CROSS_COMPILE)
export ARCH=$(_ej_val ARCH)
export PATH="$(dirname "${CROSS_COMPILE}"):${PATH}"

rm -f "${_ej_probe}"
unset -f _ej_val
unset _ej_version _ej_root _ej_cfg _ej_probe

echo "JETPACK_VERSION=${JETPACK_VERSION}"
echo "KERNEL_SRC=${KERNEL_SRC}"
echo "CROSS_COMPILE=${CROSS_COMPILE}"
echo "ARCH=${ARCH}"
