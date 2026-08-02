# Version de JetPack à utiliser par défaut pour le build.
JETPACK_VERSION ?= 6.2.1

# Fichier de configuration associé à la version choisie.
CONFIG_MK := configs/jetpack-$(JETPACK_VERSION).mk

# Vérifie que le fichier de configuration existe ; sinon, le build s'arrête.
ifeq ($(wildcard $(CONFIG_MK)),)
# Message d'erreur si la configuration demandée est absente.
$(error Config introuvable pour JETPACK_VERSION=$(JETPACK_VERSION) -> $(CONFIG_MK))
endif

# Inclusion du fichier de configuration qui définit les variables de build.
include $(CONFIG_MK)

# Export des variables importantes vers les sous-makefiles.
export JETPACK_VERSION KERNEL_SRC CROSS_COMPILE ARCH DTC BOARD_COMPATIBLE TOOLCHAIN_URL SDKMANAGER_IMAGE SDKM_OFFLINE SDKM_NON_INTERACTIVE

# Répertoire de sortie absolu pour cette version de JetPack.
OUTPUT_DIR := $(abspath output/jetpack-$(JETPACK_VERSION))

# Déclare les cibles principales comme des cibles phony afin d'éviter les conflits avec des fichiers du même nom.
.PHONY: all app driver dtbo clean setup-build-env integrate-image deploy-target flash-sdkm

# Cible par défaut : construit l'application, le driver et le DTBO.
all: app driver dtbo

# Prépare l'environnement de build une seule fois par version avant le premier build.
# Cette cible peuple workspace/sdkmanager/ avec les sources du kernel et la toolchain croisée via SDK Manager, sans flasher la carte.
# Lance le script de préparation de l'environnement de compilation.
setup-build-env:
	./scripts/setup-build-env.sh $(JETPACK_VERSION)

# Construit l'application utilisateur.
# Appelle make dans le sous-répertoire app en lui passant le répertoire de sortie.
app:
	$(MAKE) -C app OUTPUT_DIR=$(OUTPUT_DIR)/app

# Construit le module kernel du driver.
# Compile les sources du driver comme module pour le noyau Linux.
driver:
	$(MAKE) -C driver modules OUTPUT_DIR=$(OUTPUT_DIR)/driver

# Génère le DTBO (Device Tree Overlay) associé au driver.
# Construit l'overlay de device tree pour le driver.
dtbo:
	$(MAKE) -C driver dtbo OUTPUT_DIR=$(OUTPUT_DIR)/driver

# Nettoie tous les artefacts générés par les builds précédents.
# Supprime les objets et binaires de l'application.
# Supprime les objets et binaires du driver.
# Efface le répertoire de sortie complet pour cette version.
clean:
	$(MAKE) -C app clean
	$(MAKE) -C driver clean
	rm -rf $(OUTPUT_DIR)

# Déploiement à chaud sur une cible déjà flashée, depuis l'extérieur du Linux embarqué.
# Cette méthode ne reconstruit pas l'image complète, elle déploie uniquement les modules et binaires compilés.
# Exécute le script de déploiement sur la cible définie par TARGET_IP.
deploy-target: all
	./scripts/deploy-target.sh $(JETPACK_VERSION) $(OUTPUT_DIR) $(TARGET_IP)

# Intégration des artefacts dans le rootfs avant la procédure de flash depuis l'intérieur du Linux embarqué.
# Exécute le script d'intégration dans le système de fichiers racine.
integrate-image: all
	./scripts/integrate-rootfs.sh $(JETPACK_VERSION) $(OUTPUT_DIR) $(L4T_DIR)

# Flash complet de la carte en mode recovery via SDK Manager CLI avec Docker.
# Cette cible gère elle-même workspace/sdkmanager/jetpack-<version>/ et l'injection de l'application helloworld.
# Lance le script de flash complet via SDK Manager.
flash-sdkm: all
	./scripts/flash-sdkm.sh $(JETPACK_VERSION)
