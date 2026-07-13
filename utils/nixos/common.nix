{ config, lib, pkgs, ... }:

{
	#General
	nixpkgs.config.allowUnfree = true;
	networking.networkmanager.enable = true;
	time.timeZone = "America/Denver";

	#Flakes
	nix.settings.experimental-features = [ "nix-command" "flakes" ];
	nix.settings.auto-optimise-store = true;
	nix.gc = {
		automatic = true;
		dates = "weekly";
		options = "--delete-older-than 30d";
	};

	#Env
	environment.systemPackages = with pkgs; [
		vim
		wget
		git
		curl
		rsync
		htop
		alacritty
	];

	#SSH
	services.openssh = {
		enable = true;
		openFirewall = false;
		settings = {
			PasswordAuthentication = false;
			PermitRootLogin = "no";
		};
	};

	services.tailscale = {
        enable = true;
        extraUpFlags = [ "--ssh" ];
    };

	services.udev.packages = with pkgs; [
		game-devices-udev-rules
	];
	
	networking.firewall.interfaces."tailscale0".allowedTCPPorts = [ 22 ];
}
