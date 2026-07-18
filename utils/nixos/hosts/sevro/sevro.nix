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
		ethtool
		pciutils
	];

	#Boot
	boot.loader.systemd-boot.enable = true;
	boot.loader.efi.canTouchEfiVariables = true;

	#Routing
	boot.kernel.sysctl = {
		"net.ipv4.ip_forward" = 1;
		"net.ipv6.conf.all.forwarding" = 1;
	};

	services.tailscale = {
		useRoutingFeatures = "server";
		extraUpFlags = [ "--advertise-exit-node" "--advertise-routes=10.0.0.0/24" ];
	};

	# Protected LAN link to cerebro (2.5G Intel i226 card port).
	networking.networkmanager.unmanaged = [ "interface-name:enp35s0" ];
	networking.interfaces.enp35s0.ipv4.addresses = [
		{ address = "10.0.0.1"; prefixLength = 24; }
	];
	networking.nat = {
		enable = true;
		externalInterface = "enp42s0";
		internalInterfaces = [ "enp35s0" ];
	};

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
	
