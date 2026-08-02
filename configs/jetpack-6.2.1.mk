# JetPack 6.2.1 -> L4T R36.4.x, kernel 5.15, Ubuntu 22.04
WORKDIR        := $(CURDIR)/workspace/sdkmanager/jetpack-6.2.1
KERNEL_SRC     ?= $(WORKDIR)/Linux_for_Tegra/source/kernel/kernel-jammy-src
TOOLCHAIN_DIR  ?= $(WORKDIR)/toolchain
# URL exacte à relever sur la page "Jetson Linux Toolchain" NVIDIA pour R36.4.x
# (placeholder — à renseigner soi-même, l'URL exacte dépend de la release)
TOOLCHAIN_URL  ?= CHANGE_ME_toolchain_url_r36.4
CROSS_COMPILE  ?= $(TOOLCHAIN_DIR)/bin/aarch64-buildroot-linux-gnu-
ARCH           := arm64
DTC            ?= dtc
BOARD_COMPATIBLE := nvidia,p3768-0000+p3767-0000
