{ config, lib, pkgs, ... }:

{
	#General
	nixpkgs.config.allowUnfree = true;
	networking.networkmanager.enable = true;
	time.timeZone = "UTC";

	#Flakes
	nix.settings.experimental-features = [ "nix-command" "flakes" ];

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
	
	networking.firewall.allowedTCPPorts = [ 22 ];
}
