{ config, lib, pkgs, ... }:
{
    imports = [
        ./hardware-configuration.nix
        ../../profiles/work.nix
        ../../users/matthew/system.nix
        ../../users/matthew/home.nix
    ];

    networking.hostName = "swordfish";

    # Cache sudo credentials for 1 hour before re-prompting.
    security.sudo.extraConfig = ''
        Defaults timestamp_timeout=60
    '';

    services.tailscale.extraUpFlags = lib.mkForce [ ];

    #Rust toolchain
    environment.systemPackages = with pkgs; [
        rustc
        cargo
    ];

    boot.loader.systemd-boot.enable = true;
    boot.loader.efi.canTouchEfiVariables = true;
    boot.resumeDevice = "/dev/disk/by-uuid/1381050d-4ca0-408f-9ad7-30fd1c4893c7";
    boot.kernelParams = [ "resume_offset=533760" ];

    boot.initrd.systemd.enable = true;
    boot.initrd.luks.devices."cryptroot".crypttabExtraOpts = [ "tpm2-device=auto" ];


    hardware.graphics = {
        enable = true;
        enable32Bit = true;
    };

    hardware.graphics.extraPackages = with pkgs; [
        intel-media-driver
        libva-utils
    ];

# disble nvidia driver that tries to activate the unused nvidia gpu
    boot.blacklistedKernelModules = [ "nouveau" ];

    systemd.services.disable-nvidia-dgpu = {
        description = "Power off the unused NVIDIA dGPU";
        wantedBy = [ "multi-user.target" ];
        after = [ "multi-user.target" ];
        serviceConfig.Type = "oneshot";
        script = ''
            dev=/sys/bus/pci/devices/0000:01:00.0
            if [ -e "$dev/remove" ]; then
                echo 1 > "$dev/remove"
            fi
        '';
    };

    services.snapper.configs = {
        home = {
            SUBVOLUME = "/home";
            ALLOW_USERS = [ "matthew" ];
            TIMELINE_CREATE = true;
            TIMELINE_CLEANUP = true;
            TIMELINE_LIMIT_HOURLY = 5;
            TIMELINE_LIMIT_DAILY = 7;
            TIMELINE_LIMIT_WEEKLY = 4;
            TIMELINE_LIMIT_MONTHLY = 6;
            TIMMELINE_LIMIT_YEARLY = 0;
        };
    };
    services.snapper.snapshotInterval = "hourly";

    system.stateVersion = "26.05";
}
