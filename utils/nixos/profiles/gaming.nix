{ config, lib, pkgs, ... }:
{
    imports = [
        ./desktop.nix
    ];

	environment.systemPackages = with pkgs; [
        discord
	];

    programs.steam.enable = true;

}	
