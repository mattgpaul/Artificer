{ config, inputs, pkgs, ... }:
{
    imports = [ inputs.home-manager.nixosModules.default ];

    home-manager.useGlobalPkgs = true;
    home-manager.useUserPackages = true;
    home-manager.backupFileExtension = "backup";

    home-manager.users.matthew = { config, pkgs, osConfig, ... }:
    let
        waybarBase = builtins.fromJSON (builtins.readFile ../../../waybar/config.jsonc);
        waybarConfig = if osConfig.networking.hostName == "swordfish"
            then waybarBase // {
                modules-right = [ "cpu" "memory" "pulseaudio" "battery" "network" ];
                battery = {
                    interval = 10;
                    states = { good = 80; warning = 30; critical = 15; };
                    format = "{icon}  {capacity}%";
                    format-charging = "{icon}  {capacity}%";
                    format-plugged = "{icon}  {capacity}%";
                    format-full = "{icon}  {capacity}%";
                    format-icons = {
                        charging = [ "󰢜" "󰂆" "󰂇" "󰂈" "󰢝" "󰂉" "󰢞" "󰂊" "󰂋" "󰂅" ];
                        default = [ "󰁺" "󰁻" "󰁼" "󰁽" "󰁾" "󰁿" "󰂀" "󰂁" "󰂂" "󰁹" ];
                    };
                    tooltip-format = "{timeTo} ({power}W)";
                };
            }
            else waybarBase;
    in {
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
            mesa-demos
        ];

        home.sessionVariables.EDITOR = "nvim";
        
        home.file = { 
            ".config/nvim".source = ../../../nvim;
            ".config/rofi".source = ../../../rofi;
            ".config/yazi".source = ../../../yazi;
            ".config/alacritty".source = ../../../alacritty;
            ".config/hypr".source = ../../../hypr;
            ".config/waybar/style.css".source = ../../../waybar/style.css;
            ".config/waybar/config.jsonc".text = builtins.toJSON waybarConfig;
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
