{ config, lib, pkgs, ... }:
{

    #CPU
    services.tlp.enable = true;
    services.thermald.enable = true;
    services.printing.enable = true;
    services.fwupd.enable = true;

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
        HandleLidSwitch = "suspend";
        HandleLidSwitchExternalPower = "suspend";
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
	programs.hyprlock.enable = true;
	services.hypridle.enable = true;
	
	#Login
	services.displayManager.sddm.enable = true;
	services.displayManager.sddm.wayland.enable = true;
	services.displayManager.defaultSession = "hyprland";
	environment.sessionVariables.NIXOS_OZONE_WL = "1";

	#Apps
	environment.systemPackages = with pkgs; [
		bat
		btop
		rofi
		headsetcontrol
		waybar
		hyprpaper
        python313
        google-chrome
        slack
        brightnessctl
        grim
        slurp
        wl-clipboard
        cliphist
        gnumake
	];

    virtualisation.docker.rootless = {
        enable = true;
        setSocketVariable = true;
    };

    #Fonts
    fonts.packages = with pkgs; [
        nerd-fonts.jetbrains-mono
        noto-fonts
        noto-fonts-color-emoji
    ];
}
