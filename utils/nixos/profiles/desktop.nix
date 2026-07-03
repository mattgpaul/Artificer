{ config, lib, pkgs, ... }:
{
	#Hyperland
	programs.hyprland.enable = true;
	programs.hyprland.withUWSM = false;
	
	#Login
	services.displayManager.sddm.enable = true;
	services.displayManager.sddm.wayland.enable = true;
	services.displayManager.autoLogin = {
		enable = true;
		user = "matthew";
	};
	services.displayManager.defaultSession = "hyprland";

	#Apps
	programs.firefox.enable = true;
	
	environment.systemPackages = with pkgs; [
		bat
		btop
		claude-code
		kitty
		rofi
		fzf
		headsetcontrol
		neovim
		waybar
		hyprpaper
		obsidian
	];

    fonts.packages = with pkgs; [
        nerd-fonts.jetbrains-mono
    ];
}	
