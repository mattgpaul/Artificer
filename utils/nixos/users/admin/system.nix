{ config, lib, pkgs, ... }:
{
	users.users.admin = {
		isNormalUser = true;
		extraGroups = [ "wheel" "networkmanager" ];
		openssh.authorizedKeys.keys = [
			"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKptSbcOhjFj+FWlW5g19AfNdphHkux6m9IYzwoC7I1c"
				"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDOeqL/GalLrnoIrIFPl5GhYJSNgsrFr7h7+3TW5T9o0"
		];
		packages = with pkgs; [
            fzf
            tree 
		];
	};

    programs.bash = {
        enable = true;
        shellAliases = {
            gst = "git status";
            gco = "git checkout";
            glg = "git log --oneline --graph --decorate";
        };
    };

    programs.git = {
        enable = true;
        config = {
            user.name = "Matthew Paul";
            user.email = "mattgpaul@gmail.com";
            init.defaultBranch = "main";
            push.autoSetupRemote = true;
            pull.rebase = true;
            core.editor = "nvim";
        };
    };
}
