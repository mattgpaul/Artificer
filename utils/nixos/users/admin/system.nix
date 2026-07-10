{ config, lib, pkgs, ... }:
{
	users.users.admin = {
		isNormalUser = true;
		extraGroups = [ "wheel" "networkmanager" ];
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
