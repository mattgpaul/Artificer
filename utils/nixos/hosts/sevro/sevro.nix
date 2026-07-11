{ config, lib, pkgs, ... }:

{
	imports = [
        #Hardware
        ./hardware-configuration.nix
        #Desktop
		../../profiles/desktop.nix
        #Users
        ../../users/admin/system.nix
        ../../users/matthew/system.nix
        ../../users/matthew/home.nix
	];

	networking.hostName = "sevro";

	#Rust toolchain
	environment.systemPackages = with pkgs; [
		rustc
		cargo
	];

	#Boot
	boot.loader.systemd-boot.enable = true;
	boot.loader.efi.canTouchEfiVariables = true;

	#Routing
	boot.kernel.sysctl = {
		"net.ipv4.ip_forward" = 1;
		"net.ipv6.conf.all.forwarding" = 1;
	};

    services.tailscale.extraUpFlags = [ "--advertise-exit-node" ];

	#NVIDIA
	#TODO: split into its own hardware module
	services.xserver.videoDrivers = [ "nvidia" ];
	hardware.graphics = {
		enable = true;
		extraPackages = [ pkgs.nvidia-vaapi-driver ];
	};
	hardware.nvidia = {
		modesetting.enable = true;
		open = false;
		package = config.boot.kernelPackages.nvidiaPackages.legacy_580;
		nvidiaSettings = true;
	};

	system.stateVersion = "26.05";
}
	
