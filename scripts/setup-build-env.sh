#!/usr/bin/env bash
set -euo pipefail
JETPACK_VERSION=${1:?usage: setup-build-env.sh <jetpack_version>}
TARGET=${TARGET:-JETSON_ORIN_NANO_TARGETS}
WORKDIR="$(pwd)/workspace/sdkmanager/jetpack-${JETPACK_VERSION}"
SDKM_OFFLINE=${SDKM_OFFLINE:-0}
SDKM_NON_INTERACTIVE=${SDKM_NON_INTERACTIVE:-0}
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
  make JETPACK_VERSION=7.2 setup-build-env SDKMANAGER_IMAGE=sdkmanager:2.4.1.13536-Ubuntu_24.04
EOF
  return 1
}

SDKM_IMAGE=$(resolve_sdkm_image)
echo ">> Image sdkmanager utilisee : $SDKM_IMAGE"

SDKM_STATE_DIR="$WORKDIR/.nvsdkm"
mkdir -p "$SDKM_STATE_DIR"

DOCKER_TTY_ARGS=()
if ! is_truthy "$SDKM_NON_INTERACTIVE"; then
  if [ -t 0 ] && [ -t 1 ]; then
    DOCKER_TTY_ARGS=(-it)
  else
    SDKM_NON_INTERACTIVE=1
    echo ">> TTY non disponible: bascule automatique en mode non interactif."
  fi
fi

has_sdkm_session_cache() {
  [ -n "$(find "$SDKM_STATE_DIR" -mindepth 1 -type f 2>/dev/null | head -n1)" ]
}

if is_truthy "$SDKM_OFFLINE"; then
  echo ">> Mode OFFLINE actif: aucun acces internet, aucun login sdkmanager."
else
  if ! curl -fsS --max-time 5 https://static-login.nvidia.com >/dev/null 2>&1; then
    cat >&2 <<EOF
Acces internet vers static-login.nvidia.com indisponible.
Sans internet, sdkmanager ne peut pas se connecter en mode devzone.
Utilisez SDKM_OFFLINE=1 uniquement avec un cache deja pre-rempli dans:
  $WORKDIR
EOF
    exit 1
  fi

  if is_truthy "$SDKM_NON_INTERACTIVE" && ! has_sdkm_session_cache; then
    cat >&2 <<EOF
Mode non interactif demande, mais aucun etat de session sdkmanager n'est present.
Faites une premiere execution interactive pour initialiser la session:
  make JETPACK_VERSION=$JETPACK_VERSION setup-build-env
Puis relancez en non interactif.
EOF
    exit 1
  fi

  echo ">> Téléchargement du Driver Package (sdkmanager CLI, sans flash)..."
  set +e
  docker run "${DOCKER_TTY_ARGS[@]}" --rm --name sdkm_env_${JETPACK_VERSION} \
    --privileged --network host \
    -v "$WORKDIR:/home/nvidia/nvidia_sdk" \
    -v "$SDKM_STATE_DIR:/home/nvidia/.nvsdkm" \
    "$SDKM_IMAGE" --cli --action install \
    --login-type devzone \
    --product Jetson --target-os Linux \
    --version "$JETPACK_VERSION" \
    --host --target "$TARGET" \
    --select 'Jetson Linux' \
    --license accept \
    --export-logs /home/nvidia/nvidia_sdk/sdkm_logs
  sdkm_rc=$?
  set -e
  if [ "$sdkm_rc" -ne 0 ]; then
    cat >&2 <<EOF
sdkmanager a echoue (code $sdkm_rc) pendant la preparation JetPack.
Consultez les logs exportes dans:
  $WORKDIR/sdkm_logs
(ce dossier peut etre absent si sdkmanager echoue avant le demarrage de session)
Si vous n'avez pas internet, utilisez SDKM_OFFLINE=1 avec un cache deja pre-rempli.
Si vous avez internet, relancez en mode interactif pour completer le login NVIDIA.
EOF
    exit "$sdkm_rc"
  fi
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

if is_truthy "$SDKM_OFFLINE"; then
  if [ ! -d "$WORKDIR/Linux_for_Tegra/source/kernel" ]; then
    cat >&2 <<EOF
Sources noyau absentes dans $WORKDIR/Linux_for_Tegra/source/kernel.
En mode OFFLINE, lancez d'abord setup-build-env avec internet pour initialiser le cache.
EOF
    exit 1
  fi
  echo ">> Mode OFFLINE: source_sync.sh saute (cache local requis)."
else
  echo ">> Synchronisation des sources noyau (source_sync.sh)..."
  ( cd "$WORKDIR/Linux_for_Tegra/source" && ./source_sync.sh -k )
fi

if [ -x "${CROSS_COMPILE}gcc" ]; then
  echo ">> Toolchain deja presente: ${CROSS_COMPILE}gcc"
elif is_truthy "$SDKM_OFFLINE"; then
  cat >&2 <<EOF
Toolchain absente: ${CROSS_COMPILE}gcc
En mode OFFLINE, elle doit deja etre presente dans $WORKDIR/toolchain.
EOF
  exit 1
else
  echo ">> Téléchargement de la toolchain croisée..."
  : "${TOOLCHAIN_URL:?TOOLCHAIN_URL doit être défini dans configs/jetpack-${JETPACK_VERSION}.mk}"
  mkdir -p "$WORKDIR/toolchain"
  curl -fL "$TOOLCHAIN_URL" | tar -xJ -C "$WORKDIR/toolchain" --strip-components=1
fi

echo ">> Environnement prêt sous $WORKDIR :"
echo "   KERNEL_SRC    -> Linux_for_Tegra/source/kernel/<kernel-xxx>"
echo "   TOOLCHAIN_DIR -> toolchain/"
