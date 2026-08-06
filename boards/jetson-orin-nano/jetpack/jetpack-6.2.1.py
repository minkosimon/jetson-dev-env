"""JetPack 6.2.1 URL definition for Jetson Orin Nano."""

JETPACK_DEFINITION = {
	
	"jetpack_info_version": "6.2.1",
    "jetson_linux": "36.4.3",
    "kernel_version" : "kernel 5.10",
    "V4L2" : "1.20",
    "distro_version" : "L4T Ubuntu 22.04 ",
	"jetpack_info_l4t_release": "R36.4.3",
	"jetpack_url_driver_package": {"Linux_for_Tegra":"https://developer.nvidia.com/downloads/embedded/l4t/r36_release_v4.3/release/Jetson_Linux_r36.4.3_aarch64.tbz2"},
	"jetapack_url_sample_rootfs": {"Sample_rootfs":"https://developer.nvidia.com/downloads/embedded/l4t/r36_release_v4.3/sources/ubuntu_jammy-l4t_aarch64_src.tbz2"},
	"jetpack_url_toolchain": {"Toolchain":"https://developer.nvidia.com/downloads/embedded/l4t/r36_release_v3.0/toolchain/aarch64--glibc--stable-2022.08-1.tar.bz2"}
}
