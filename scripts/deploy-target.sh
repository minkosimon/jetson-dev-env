#!/usr/bin/env bash
# Dépôt "hors image" : scp du binaire app + du .ko + de l'overlay vers une carte déjà flashée,
# puis insmod à chaud. Ne modifie jamais l'image ; à refaire à chaque reboot tant que le module
# n'est pas intégré via integrate-rootfs.sh.
set -euo pipefail

JETPACK_VERSION=${1:?usage: deploy-target.sh <jetpack_version> <output_dir> <target_ip>}
OUTPUT_DIR=${2:?usage: deploy-target.sh <jetpack_version> <output_dir> <target_ip>}
TARGET_IP=${3:?usage: deploy-target.sh <jetpack_version> <output_dir> <target_ip>}
TARGET_USER=${TARGET_USER:-nvidia}
TARGET_SSH="${TARGET_USER}@${TARGET_IP}"

APP_BIN="${OUTPUT_DIR}/app/helloworld_app"
DRV_KO="${OUTPUT_DIR}/driver/helloworld_drv.ko"
OVERLAY_DTBO="${OUTPUT_DIR}/driver/helloworld-overlay.dtbo"

for f in "$APP_BIN" "$DRV_KO" "$OVERLAY_DTBO"; do
	[ -f "$f" ] || { echo "Artefact manquant : $f (lancer 'make all' d'abord)" >&2; exit 1; }
done

echo ">> Copie vers ${TARGET_SSH}..."
scp "$APP_BIN" "$DRV_KO" "$OVERLAY_DTBO" "${TARGET_SSH}:/tmp/"

echo ">> Installation + insmod à chaud sur la cible..."
ssh "${TARGET_SSH}" bash -s <<-EOF
	set -euo pipefail
	sudo install -m 0755 /tmp/helloworld_app /usr/local/bin/helloworld_app
	sudo rmmod helloworld_drv 2>/dev/null || true
	sudo insmod /tmp/helloworld_drv.ko
	sudo mkdir -p /boot/overlays
	sudo cp /tmp/helloworld-overlay.dtbo /boot/overlays/
	rm -f /tmp/helloworld_app /tmp/helloworld_drv.ko /tmp/helloworld-overlay.dtbo
	echo "Module chargé (voir dmesg), overlay copié dans /boot/overlays (application au prochain boot via extlinux.conf)."
EOF

echo ">> Déploiement JetPack ${JETPACK_VERSION} terminé sur ${TARGET_IP}."
