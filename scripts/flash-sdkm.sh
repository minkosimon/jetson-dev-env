#!/usr/bin/env bash
set -euo pipefail
JETPACK_VERSION=${1:?usage: flash-sdkm.sh <jetpack_version>}
TARGET=${TARGET:-JETSON_ORIN_NANO_TARGETS}
SDKM_OFFLINE=${SDKM_OFFLINE:-0}
SDKM_NON_INTERACTIVE=${SDKM_NON_INTERACTIVE:-0}

# workspace local au repo, non versionné (.gitignore), jetable
WORKDIR="$(pwd)/workspace/sdkmanager/jetpack-${JETPACK_VERSION}"
mkdir -p "$WORKDIR"

is_truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

resolve_sdkm_image() {
  if [ -n "${SDKMANAGER_IMAGE:-}" ]; then
    echo "$SDKMANAGER_IMAGE"
    return 0
  fi

  if docker image inspect sdkmanager:latest >/dev/null 2>&1; then
    echo "sdkmanager:latest"
    return 0
  fi

  if docker image inspect sdkmanager:2.4.1.13536-Ubuntu_24.04 >/dev/null 2>&1; then
    echo "sdkmanager:2.4.1.13536-Ubuntu_24.04"
    return 0
  fi

  local found
  found=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep '^sdkmanager:' | head -n1 || true)
  if [ -n "$found" ]; then
    echo "$found"
    return 0
  fi

  cat >&2 <<'EOF'
Aucune image Docker sdkmanager n'a ete trouvee localement.
Construisez ou taggez une image, par exemple :
  docker tag sdkmanager:2.4.1.13536-Ubuntu_24.04 sdkmanager:latest

Vous pouvez aussi forcer une image specifique :
  make JETPACK_VERSION=7.2 flash-sdkm SDKMANAGER_IMAGE=sdkmanager:2.4.1.13536-Ubuntu_24.04
EOF
  return 1
}

SDKM_IMAGE=$(resolve_sdkm_image)
echo ">> Image sdkmanager utilisee : $SDKM_IMAGE"

SDKM_STATE_DIR="$WORKDIR/.nvsdkm"
mkdir -p "$SDKM_STATE_DIR"

DOCKER_TTY_ARGS=()
if ! is_truthy "$SDKM_NON_INTERACTIVE"; then
  DOCKER_TTY_ARGS=(-it)
fi

DOCKER_COMMON=(--privileged --network host
  -v /dev/bus/usb:/dev/bus/usb -v /dev:/dev
  -v "$WORKDIR:/home/nvidia/nvidia_sdk"
  -v "$SDKM_STATE_DIR:/home/nvidia/.nvsdkm")

if is_truthy "$SDKM_OFFLINE"; then
  echo ">> Mode OFFLINE actif: preparation BSP via sdkmanager sautee (cache local requis)."
else
  echo ">> Préparation du BSP JetPack $JETPACK_VERSION (sans flash)..."
  docker run "${DOCKER_TTY_ARGS[@]}" --rm --name sdkm_prep_${JETPACK_VERSION} "${DOCKER_COMMON[@]}" \
    "$SDKM_IMAGE" --cli --action install \
    --login-type devzone \
    --product Jetson --target-os Linux \
    --version "$JETPACK_VERSION" \
    --host --target "$TARGET" \
    --select 'Jetson Linux' \
    --license accept
fi

# sdkmanager écrit dans WORKDIR/JetPack_<version>_Linux_<target>/Linux_for_Tegra ;
# on normalise via un lien symbolique pour garder une arborescence prévisible.
REAL_L4T=$(find "$WORKDIR" -maxdepth 2 -type d -name Linux_for_Tegra | head -n1)
if [ -z "$REAL_L4T" ] && [ -d "$WORKDIR/Linux_for_Tegra" ]; then
  REAL_L4T="$WORKDIR/Linux_for_Tegra"
fi
if [ -z "$REAL_L4T" ]; then
  cat >&2 <<EOF
Linux_for_Tegra introuvable dans $WORKDIR.
En mode OFFLINE, il faut pre-remplir ce dossier via une execution online precedente.
EOF
  exit 1
fi
ln -sfn "$REAL_L4T" "$WORKDIR/Linux_for_Tegra"
L4T_DIR="$WORKDIR/Linux_for_Tegra"

echo ">> Injection helloworld dans $L4T_DIR/rootfs ..."
./scripts/integrate-rootfs.sh "$JETPACK_VERSION" "output/jetpack-${JETPACK_VERSION}" "$L4T_DIR"

echo ">> Vérification du mode recovery..."
lsusb | grep -qi "0955:7523" || {
  echo "Carte non détectée en Force Recovery Mode (0955:7523 APX). Abandon." >&2
  exit 1
}

echo ">> Flash JetPack $JETPACK_VERSION sur $TARGET..."
docker run "${DOCKER_TTY_ARGS[@]}" --rm --name sdkm_flash_${JETPACK_VERSION} "${DOCKER_COMMON[@]}" \
  "$SDKM_IMAGE" --cli --action install \
  --login-type devzone \
  --product Jetson --target-os Linux \
  --version "$JETPACK_VERSION" \
  --host --target "$TARGET" \
  --select 'Jetson Linux' \
  --flash --license accept
