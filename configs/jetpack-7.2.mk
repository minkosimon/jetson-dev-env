# JetPack 7.2 -> L4T R39.x, kernel 6.8, Ubuntu 24.04
WORKDIR        := $(CURDIR)/workspace/sdkmanager/jetpack-7.2
KERNEL_SRC     ?= $(WORKDIR)/Linux_for_Tegra/source/kernel/kernel-6.8
TOOLCHAIN_DIR  ?= $(WORKDIR)/toolchain
# URL exacte à relever sur la page "Jetson Linux Toolchain" NVIDIA pour R39.x
# (placeholder — à renseigner soi-même, l'URL exacte dépend de la release)
TOOLCHAIN_URL  ?= CHANGE_ME_toolchain_url_r39
CROSS_COMPILE  ?= $(TOOLCHAIN_DIR)/bin/aarch64-linux-gnu-
ARCH           := arm64
DTC            ?= dtc
BOARD_COMPATIBLE := nvidia,p3768-0000+p3767-0000
