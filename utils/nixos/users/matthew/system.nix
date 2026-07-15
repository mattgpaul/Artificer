{ config, lib, pkgs, ... }:
{
	users.users.matthew = {
		isNormalUser = true;
		extraGroups = [ "wheel" "networkmanager" "docker" ];
		openssh.authorizedKeys.keys = [
			"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKptSbcOhjFj+FWlW5g19AfNdphHkux6m9IYzwoC7I1c"
				"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDOeqL/GalLrnoIrIFPl5GhYJSNgsrFr7h7+3TW5T9o0"
		];
		packages = with pkgs; [
			claude-code
				fzf
				obsidian
				tree 
		];
	};

    programs.bash = {
        enable = true;
        shellAliases = {
            gst = "git status";
            gco = "git checkout";
            glg = "git log --oneline --graph --decorate";
            nrs = "sudo nixos-rebuild switch";
            nrt = "sudo nixos-rebuild test";
            nrb = "sudo nixos-rebuild boot";
        };
    };

}
