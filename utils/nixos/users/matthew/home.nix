{ config, inputs, pkgs, ... }:
{
    imports = [ inputs.home-manager.nixosModules.default ];

    home-manager.useGlobalPkgs = true;
    home-manager.useUserPackages = true;
    home-manager.backupFileExtension = "backup";

    home-manager.users.matthew = { config, pkgs, osConfig, ... }:
    let
        waybarBase = builtins.fromJSON (builtins.readFile ../../../waybar/config.jsonc);
        waybarConfig = waybarBase;
    in {
        imports = [ ./ghostty-home.nix ];

        home.username = "matthew";
        home.homeDirectory = "/home/matthew";
        home.stateVersion = "26.05";
        programs.home-manager.enable = true;
        programs.bash = {
            enable = true;
            shellAliases = {
                jst = "jj status";
                jjl = "jj log";
                jjd = "jj describe";
            };
            initExtra = ''
                PS1='\[\e]0;\u@\h: \w\a\]\n\[\e[1m\]\[\e[38;5;46m\]\u\[\e[38;5;38m\]@\[\e[38;5;166m\]\H\[\e[39m\]:\[\e[38;5;39m\]\w\[\e[39m\]\$\[\e[0m\] '
                # services.ssh-agent exports SSH_AUTH_SOCK only in ~/.profile (login
                # shells). Interactive non-login shells (terminals under Hyprland) read
                # .bashrc, not .profile, so point them at the running agent's socket too.
                # Without this, `ssh -A` has no agent to forward.
                export SSH_AUTH_SOCK="''${XDG_RUNTIME_DIR}/ssh-agent"
                # Same story for rootless Docker: virtualisation.docker.rootless.setSocketVariable
                # only exports DOCKER_HOST in login shells, so terminals under Hyprland miss it and
                # fall back to the root-owned /var/run/docker.sock ("permission denied"). Point them
                # at the rootless socket so `docker` works with no sudo and no docker group.
                export DOCKER_HOST="unix://''${XDG_RUNTIME_DIR}/docker.sock"
               [ -f "$HOME/.config/secrets/bash.env" ] && source "$HOME/.config/secrets/bash.env"
                # Reuse the parked yazi instead of nesting a new one: if we're already
                # inside a shell that yazi spawned ($YAZI_LEVEL set), just exit back to it.
                y() {
                    if [ -n "$YAZI_LEVEL" ]; then
                        exit
                    else
                        command yazi "$@"
                    fi
                }
            '';
        };

        programs.git = {
            enable = true;
            settings = {
                user.name = "Matthew Paul";
                user.email = "mattgpaul@gmail.com";
                init.defaultBranch = "main";
                push.autoSetupRemote = true;
                pull.rebase = true;
                core.editor = "nvim";
            };
        };
        programs.direnv = {
            enable = true;
            nix-direnv.enable = true;
        };

        services.ssh-agent.enable = true;

        # Eagerly load the key into the agent on login so `ssh -A` forwarding works
        # immediately (agents start empty across reboots). Key is passphrase-less, so
        # this needs no askpass. %t = XDG_RUNTIME_DIR, %h = home.
        systemd.user.services.ssh-add-keys = {
            Unit = {
                Description = "Load SSH keys into ssh-agent";
                After = [ "ssh-agent.service" ];
                Requires = [ "ssh-agent.service" ];
            };
            Service = {
                Type = "oneshot";
                Environment = "SSH_AUTH_SOCK=%t/ssh-agent";
                ExecStart = "${pkgs.openssh}/bin/ssh-add %h/.ssh/id_ed25519";
            };
            Install.WantedBy = [ "default.target" ];
        };
    home.packages = with pkgs; [
        (neovim.override { viAlias = true; vimAlias = true; })
        bibata-cursors
        fd
        pyright
        rust-analyzer
        ripgrep
        mesa-demos
        yazi
        jujutsu
        mdcat
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
            ".config/opencode/opencode.json".source = ../../../opencode/opencode.json;
            # Docker/devcontainer bind-mounts expect ~/.gitconfig to exist; without it
            # Docker recreates it as a root-owned dir and breaks git. Point it at the
            # real (XDG) config that programs.git writes.
            ".gitconfig".source = config.lib.file.mkOutOfStoreSymlink "${config.home.homeDirectory}/.config/git/config";
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
                "\\C-p" = "\"y\\n\"";
            };
            extraConfig = ''
                set colored-stats on
                set completion-ignore-case on
                set show-all-if-ambiguous on
            '';
        };
    };
}
