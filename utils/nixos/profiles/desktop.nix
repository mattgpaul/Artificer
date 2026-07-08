{ config, lib, pkgs, ... }:
{
	#Sound
	security.rtkit.enable = true;
	services.pipewire = {
		enable = true;
		alsa.enable = true;
		alsa.support32Bit = true;
		pulse.enable = true;
		jack.enable = true;
	};

	#Hyperland
	programs.hyprland.enable = true;
	programs.hyprland.withUWSM = false;
	programs.hyprlock.enable = true;
	services.hypridle.enable = lib.mkForce false;
	
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
		kitty
		rofi
		headsetcontrol
		waybar
		hyprpaper
        python313
        grim
        slurp
        wl-clipboard
        cliphist
	];

    fonts.packages = with pkgs; [
        nerd-fonts.jetbrains-mono
    ];
}	
