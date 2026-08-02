# jetson-helloworld

Squelette de dev pour Jetson Orin Nano (app userspace + driver kernel `helloworld`), multi-JetPack
(6.2 → 7.2). Voir `jetson-helloworld-projet.md` pour la spécification complète du projet.

- JetPack 6.x → L4T R36.x, kernel 5.15, Ubuntu 22.04.
- JetPack 7.x → L4T R39.x, kernel 6.8, Ubuntu 24.04.

Le repo ne contient aucun chemin en dur vers une installation JetPack : tout ce qui dépend de la
version (sources kernel, toolchain, `compatible` de la carte) est injecté via
`configs/jetpack-X.mk`, sélectionné par `JETPACK_VERSION` au moment du build.

## Prérequis

- Docker installé (le Driver Package NVIDIA + les sources noyau + la toolchain croisée sont
  téléchargés via `sdkmanager` en CLI par `make setup-build-env`, pas d'installation manuelle
  requise).
- Une image Docker `sdkmanager` doit exister localement. Si elle n'est pas taggée en `latest`,
  vous pouvez soit l'indiquer via `SDKMANAGER_IMAGE=...`, soit créer le tag :
  `docker tag sdkmanager:2.4.1.13536-Ubuntu_24.04 sdkmanager:latest`.
- Avant le premier `setup-build-env` d'une version donnée, renseigner `TOOLCHAIN_URL` dans
  `configs/jetpack-X.mk` (placeholder `CHANGE_ME_toolchain_url_rXX` à remplacer par l'URL exacte
  relevée sur la page NVIDIA _Jetson Linux Toolchain_ de la release R36.x/R39.x concernée).
- `dtc` pour compiler l'overlay.
- Compte NVIDIA Developer (login `sdkmanager` déclenché au premier appel, via une URL à ouvrir
  dans un navigateur — à faire une seule fois).
- Sans Internet, `sdkmanager` ne peut pas faire de premier login ni de téléchargement: utilisez
  `SDKM_OFFLINE=1` uniquement si `workspace/sdkmanager/jetpack-<version>/` est déjà prérempli.

## Utilisation

```bash
# Étape 0 (une fois par version) : peuple workspace/ avec sources noyau + toolchain croisée
make JETPACK_VERSION=6.2.1 setup-build-env
make JETPACK_VERSION=7.2   setup-build-env
make JETPACK_VERSION=7.2   setup-build-env SDKMANAGER_IMAGE=sdkmanager:2.4.1.13536-Ubuntu_24.04

# Mode non interactif (pas de TTY Docker) : nécessite un état d'auth déjà en cache
make JETPACK_VERSION=7.2 setup-build-env SDKM_NON_INTERACTIVE=1

# Mode offline + non interactif (aucun accès Internet) : cache local obligatoire
make JETPACK_VERSION=7.2 setup-build-env SDKM_OFFLINE=1 SDKM_NON_INTERACTIVE=1

# Build complet pour JetPack 6.2.1
make JETPACK_VERSION=6.2.1 all

# Build complet pour JetPack 7.2
make JETPACK_VERSION=7.2 all

# Test rapide de l'app en local (hôte, sans toolchain croisée)
make -C app host

# Test rapide sur une carte déjà flashée (hors image)
make JETPACK_VERSION=7.2 deploy-target TARGET_IP=192.168.1.50

# Intégration dans le rootfs avant un flash manuel (BSP déjà extrait ailleurs)
make JETPACK_VERSION=7.2 integrate-image L4T_DIR=/chemin/vers/un/Linux_for_Tegra/deja/extrait

# Flash complet en mode recovery via SDK Manager CLI Docker
make JETPACK_VERSION=7.2 flash-sdkm

# Flash non interactif (pas de TTY Docker) : nécessite un état d'auth déjà en cache
make JETPACK_VERSION=7.2 flash-sdkm SDKM_NON_INTERACTIVE=1

# Flash offline + non interactif : cache BSP local obligatoire
make JETPACK_VERSION=7.2 flash-sdkm SDKM_OFFLINE=1 SDKM_NON_INTERACTIVE=1
```

`setup-build-env` et `flash-sdkm` partagent le même cache `workspace/sdkmanager/jetpack-<version>/`
(non versionné) : le premier le peuple avec les sources noyau + la toolchain (pas de flash, pas de
carte requise), le second réutilise/complète ce cache pour flasher réellement une carte en
recovery mode. Chaque version de build produit ses artefacts dans `output/jetpack-<version>/`.
Aucun des deux répertoires n'est versionné, et aucun n'écrit dans `app/` ou `driver/`.

## Arborescence

```
jetson-helloworld/
├── Makefile                # orchestrateur top-level
├── configs/                # un .mk par version JetPack (chemins kernel/toolchain locaux)
├── app/                    # appli userspace (ioctl vers /dev/helloworld)
├── driver/                 # module kernel + overlay DT
└── scripts/                # env, setup build-env (sdkmanager), deploy hors-image,
                            # intégration rootfs, flash sdkmanager
```
