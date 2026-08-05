"""JetPack 7.2 URL definition for Jetson Orin Nano."""

JETPACK_DEFINITION = {
	
	"jetpack_info_version": "7.2",
    "jetson_linux": "39.2",
    "kernel_version" : "kernel 6.8",
    "V4L2" : "1.22.1",
    "distro_version" : "L4T Ubuntu 24.04 ",
	"jetpack_info_l4t_release": "R39.2 (06/02/2026)",
	"jetpack_url_driver_package": {"Linux_for_Tegra":"https://developer.nvidia.com/downloads/embedded/L4T/r39_Release_v2.0/release/Jetson_Linux_R39.2.0_aarch64.tbz2"},
	"jetapack_url_sample_rootfs": {"Sample_rootfs":"https://developer.nvidia.com/downloads/embedded/L4T/r39_Release_v2.0/release/Tegra_Linux_Sample-Root-Filesystem_R39.2.0_aarch64.tbz2"},
	"jetpack_url_toolchain": {"Toolchain":"https://developer.nvidia.com/downloads/embedded/L4T/r38_Release_v2.0/release/x-tools.tbz2"}
}
