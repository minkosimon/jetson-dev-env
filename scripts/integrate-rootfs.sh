#!/usr/bin/env bash
# Intégration "dans l'image" : copie app/driver/overlay dans le rootfs d'un Linux_for_Tegra
# AVANT apply_binaries.sh/flash.sh, pour qu'ils soient gravés dans l'image au prochain flash.
# KERNEL_SRC est repris de l'environnement (exporté par le Makefile top-level via configs/*.mk).
set -euo pipefail

JETPACK_VERSION=${1:?usage: integrate-rootfs.sh <jetpack_version> <output_dir> <l4t_dir>}
OUTPUT_DIR=${2:?usage: integrate-rootfs.sh <jetpack_version> <output_dir> <l4t_dir>}
L4T_DIR=${3:?usage: integrate-rootfs.sh <jetpack_version> <output_dir> <l4t_dir>}
: "${KERNEL_SRC:?KERNEL_SRC non défini (source scripts/env-jetpack.sh ou lancer via make)}"

ROOTFS="${L4T_DIR}/rootfs"
[ -d "$ROOTFS" ] || { echo "rootfs introuvable : $ROOTFS" >&2; exit 1; }

APP_BIN="${OUTPUT_DIR}/app/helloworld_app"
DRV_KO="${OUTPUT_DIR}/driver/helloworld_drv.ko"
OVERLAY_DTBO="${OUTPUT_DIR}/driver/helloworld-overlay.dtbo"
for f in "$APP_BIN" "$DRV_KO" "$OVERLAY_DTBO"; do
	[ -f "$f" ] || { echo "Artefact manquant : $f (lancer 'make all' d'abord)" >&2; exit 1; }
done

KVER=$(awk '
	/^VERSION *=/    { v=$3 }
	/^PATCHLEVEL *=/ { p=$3 }
	/^SUBLEVEL *=/   { s=$3 }
	/^EXTRAVERSION *=/ { e=$3 }
	END { printf "%s.%s.%s%s", v, p, s, e }
' "${KERNEL_SRC}/Makefile")
echo ">> Version kernel détectée : ${KVER}"

echo ">> Copie helloworld_app -> rootfs/usr/local/bin/"
sudo install -m 0755 "$APP_BIN" "${ROOTFS}/usr/local/bin/helloworld_app"

MODDIR="${ROOTFS}/lib/modules/${KVER}/extra"
echo ">> Copie helloworld_drv.ko -> ${MODDIR#$ROOTFS}/"
sudo mkdir -p "$MODDIR"
sudo install -m 0644 "$DRV_KO" "${MODDIR}/helloworld_drv.ko"

echo ">> depmod en chroot (nécessite binfmt qemu-aarch64 enregistré sur le host)..."
sudo chroot "$ROOTFS" depmod "$KVER"

echo ">> Copie overlay -> rootfs/boot/"
sudo mkdir -p "${ROOTFS}/boot"
sudo install -m 0644 "$OVERLAY_DTBO" "${ROOTFS}/boot/helloworld-overlay.dtbo"

EXTLINUX="${ROOTFS}/boot/extlinux/extlinux.conf"
if [ -f "$EXTLINUX" ]; then
	if grep -q '^\s*OVERLAYS.*helloworld-overlay.dtbo' "$EXTLINUX"; then
		echo ">> extlinux.conf déjà patché, rien à faire."
	else
		echo ">> Patch de extlinux.conf (ajout OVERLAYS)..."
		sudo sed -i '/^\s*FDT /a\      OVERLAYS /boot/helloworld-overlay.dtbo' "$EXTLINUX"
	fi
else
	echo "extlinux.conf introuvable dans $ROOTFS, patch manuel requis." >&2
fi

echo ">> Intégration JetPack ${JETPACK_VERSION} terminée dans ${ROOTFS}."
