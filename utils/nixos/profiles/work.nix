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
	services.displayManager.autoLogin = {
		enable = true;
		user = "matthew";
	};
	services.displayManager.defaultSession = "hyprland";

	# Run Chromium/Electron apps (Chrome, Slack) on native Wayland instead of
	# XWayland: faster, sharper, proper GPU use.
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
        # --password-store=basic: skip the D-Bus secret-service probe at startup
        #   (no keyring daemon runs on this host) which otherwise stalls launch.
        # --use-angle=gl: avoid the eglCreateContext version-retry seen in logs;
        #   try =vulkan instead if gl doesn't help (Intel Iris Xe supports both).
        (google-chrome.override { commandLineArgs = "--password-store=basic --use-angle=gl"; })
        slack
        brightnessctl
        grim
        slurp
        wl-clipboard
        cliphist
	];

    #Fonts
    fonts.packages = with pkgs; [
        nerd-fonts.jetbrains-mono
        noto-fonts
        noto-fonts-color-emoji
    ];

    # Chrome launch behavior (work host only — desktops don't install Chrome).
    # Two desktop entries, merged into matthew's home-manager config:
    #  - google-chrome.desktop shadows the system one and stays the default
    #    http/https handler, so clicked links open as TABS. Hidden from launchers
    #    (NoDisplay) so it doesn't duplicate the launcher below.
    #  - google-chrome-window.desktop is what rofi shows; launching it always
    #    opens a NEW WINDOW.
    # (--password-store=basic is baked into the wrapped binary above.)
    home-manager.users.matthew.home.file = {
        ".local/share/applications/google-chrome.desktop".text = ''
            [Desktop Entry]
            Version=1.0
            Name=Google Chrome
            GenericName=Web Browser
            Comment=Access the Internet
            Exec=google-chrome-stable %U
            StartupNotify=true
            Terminal=false
            Icon=google-chrome
            Type=Application
            Categories=Network;WebBrowser;
            MimeType=application/pdf;application/xhtml+xml;application/xml;image/gif;image/jpeg;image/png;image/webp;text/html;text/xml;x-scheme-handler/http;x-scheme-handler/https;x-scheme-handler/about;x-scheme-handler/unknown;x-scheme-handler/google-chrome;
            NoDisplay=true
            Actions=new-window;new-private-window;

            [Desktop Action new-window]
            Name=New Window
            Exec=google-chrome-stable --new-window

            [Desktop Action new-private-window]
            Name=New Incognito Window
            Exec=google-chrome-stable --incognito
          '';

        ".local/share/applications/google-chrome-window.desktop".text = ''
            [Desktop Entry]
            Version=1.0
            Name=Google Chrome
            GenericName=Web Browser
            Comment=Open a new Chrome window
            Exec=google-chrome-stable --new-window %U
            StartupNotify=true
            Terminal=false
            Icon=google-chrome
            Type=Application
            Categories=Network;WebBrowser;
            Actions=new-window;new-private-window;

            [Desktop Action new-window]
            Name=New Window
            Exec=google-chrome-stable --new-window

            [Desktop Action new-private-window]
            Name=New Incognito Window
            Exec=google-chrome-stable --incognito
          '';
    };
}
