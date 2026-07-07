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

    boot.kernel.sysctl = {
        "net.ipv4.ip_forward" = 1;
        "net.ipv6.conf.all.forwarding" = 1;
    };

    hardware.graphics = {
        enable = true;
        enable32Bit = true;
    };
    
    system.stateVersion = "26.05";
}
