{ config, lib, pkgs, ... }:
{
    imports = [
        ./hardware-configuration.nix
        ../../profiles/work.nix
        ../../users/matthew/system.nix
        ../../users/matthew/home.nix
    ];

    networking.hostName = "swordfish";

    boot.loader.systemd-boot.enable = true;
    boot.loader.efi.canTouchEfiVariables = true;
    boot.resumeDevice = "/dev/disk/by-uuid/1381050d-4ca0-408f-9ad7-30fd1c4893c7";
    boot.kernelParams = [ "resume_offset=533760" ];

    boot.kernel.sysctl = {
        "net.ipv4.ip_forward" = 1;
        "net.ipv6.conf.all.forwarding" = 1;
    };

    hardware.graphics = {
        enable = true;
        enable32Bit = true;
    };

    hardware.graphics.extraPackages = with pkgs; [
        intel-media-driver
        libva-utils
    ];

    # Hybrid graphics: Intel Iris Xe (primary) + NVIDIA RTX 3050 Ti (unused).
    # nouveau can't wake the Ampere dGPU out of D3hot, so opening its render
    # node (/dev/dri/renderD129) blocks ~19s. Every Chromium/Electron app probes
    # all render nodes at startup, so Chrome/Slack/Obsidian hung for ~10-20s each.
    # We don't use the dGPU here, so blacklist nouveau (removes the hanging node)
    # and power the card off the PCI bus at boot to save battery.
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

    system.stateVersion = "26.05";
}
