{ config, lib, pkgs, ... }:
{

    #CPU
    services.tlp.enable = true;
    services.printing.enable = true;

    #Trackpad
    services.libinput.enable = true;

    #Bluetooth
    hardware.bluetooth = {
        enable = true;
        powerOnBoot = false;
    };
    services.blueman.enable = true;

    #Power
    powerManagement.enable = true;

    #Lid
    services.logind.settings.Login = {
        HandleLidSwitch = "poweroff";
        HandleLidSwitchExternalPower = "lock";
        HandleLidSwitchDocked = "ignore";
    };
    
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
	
	#Login
	services.displayManager.sddm.enable = true;
	services.displayManager.sddm.wayland.enable = true;
	services.displayManager.autoLogin = {
		enable = true;
		user = "matthew";
	};
	services.displayManager.defaultSession = "hyprland";

	#Apps
	environment.systemPackages = with pkgs; [
		bat
		btop
		rofi
		headsetcontrol
		waybar
		hyprpaper
        python313
	];

    #Fonts
    fonts.packages = with pkgs; [
        nerd-fonts.jetbrains-mono
    ];
}	
