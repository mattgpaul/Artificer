{ config, inputs, pkgs, ... }:
{
    imports = [ inputs.home-manager.nixosModules.default ];

    home-manager.useGlobalPkgs = true;
    home-manager.useUserPackages = true;
    home-manager.backupFileExtension = "backup";

    home-manager.users.matthew = { config, pkgs, ... }: {
        home.username = "matthew";
        home.homeDirectory = "/home/matthew";
        home.stateVersion = "26.05";
        programs.home-manager.enable = true;
        programs.bash = {
            enable = true;
            initExtra = ''
                PS1='\[\e]0;\u@\h: \w\a\]\n\[\e[1m\]\[\e[38;5;46m\]\u\[\e[38;5;38m\]@\[\e[38;5;166m\]\H\[\e[39m\]:\[\e[38;5;39m\]\w\[\e[39m\]\$\[\e[0m\] '
            '';
        };
        home.packages = with pkgs; [
            (neovim.override { viAlias = true; vimAlias = true; })
            bibata-cursors
            pyright
            rust-analyzer
            ripgrep
        ];

        home.sessionVariables.EDITOR = "nvim";
        
        home.file = let
            repo = "${config.home.homeDirectory}/Artificer/utils";
            link = config.lib.file.mkOutOfStoreSymlink;
        in {
            ".config/nvim".source = link "${repo}/nvim";
            ".config/rofi".source = link "${repo}/rofi";
            ".config/alacritty".source = link "${repo}/alacritty";
            ".config/hypr".source = link "${repo}/hypr";
            ".config/waybar".source = link "${repo}/waybar";
        };

        programs.fzf = {
            enable = true;
            enableBashIntegration = true;
        };

        programs.readline = {
            enable = true;
            bindings = {
                "\\e[A" = "history-search-backward";
                "\\e[B" = "history-search-forward";
            };
            extraConfig = ''
                set colored-stats on
                set completion-ignore-case on
                set show-all-if-ambiguous on
            '';
        };
    };
}
