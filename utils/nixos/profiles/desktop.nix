{ config, lib, pkgs, ... }:
{
	#Hyperland
	programs.niri.enable = true;
	
	#Login
	services.displayManager.sddm.enable = true;
	services.displayManager.sddm.wayland.enable = true;

	#Apps
	programs.firefox.enable = true;
	
	environment.systemPackages = with pkgs; [
		bat
		btop
		claude-code
		rofi
		fzf
		headsetcontrol
		neovim
		waybar
	];
}	
