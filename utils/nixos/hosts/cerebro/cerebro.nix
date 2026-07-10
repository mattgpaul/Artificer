{ config, lib, pkgs, ... }:
{
    imports = [
        ./hardware-configuration.nix
        ../../profiles/gaming.nix
        ../../users/admin/system.nix
        ../../users/matthew/system.nix
        ../../users/matthew/home.nix
    ];

    networking.hostName = "cerebro";

    boot.loader.systemd-boot.enable = true;
    boot.loader.efi.canTouchEfiVariables = true;
    boot.initrd.kernelModules = [ "amdgpu" ];

# may not need AMD drivers, documentation says they work out of the box
# GPU acceleration just needs to be enabled apparently
    
    hardware.graphics = {
            enable = true;
            enable32Bit = true;
        };

    system.stateVersion = "26.05";
}
