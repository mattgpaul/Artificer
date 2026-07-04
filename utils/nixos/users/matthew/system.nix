{ config, lib, pkgs, ... }:
{
	users.users.matthew = {
		isNormalUser = true;
		extraGroups = [ "wheel" "networkmanager" ];
		openssh.authorizedKeys.keys = [
		      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKptSbcOhjFj+FWlW5g19AfNdphHkux6m9IYzwoC7I1c"
		      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDOeqL/GalLrnoIrIFPl5GhYJSNgsrFr7h7+3TW5T9o0"
		];
		packages = with pkgs; [
        claude-code
        fzf
        neovim
        obsidian
        jujutsu
        tree 
        ];
	};
}
