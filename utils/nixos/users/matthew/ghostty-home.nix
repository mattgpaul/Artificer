# Ghostty terminal — home-manager module.
#
# Imported from within `home-manager.users.matthew` in both home.nix and work.nix,
# so ghostty is installed *only* on hosts that run home-manager for this user.
# Headless hosts (servers/rpis) never import those files, so they fall back to the
# alacritty binary declared system-wide in common.nix.
#
# Ghostty is chosen for its native Kitty graphics protocol support (inline image
# rendering), which alacritty lacks.
{ ... }:
{
    # Symlink the dead-world theme into the ghostty config dir so `theme = "dead-world"`
    # resolves it. The programs.ghostty module owns ~/.config/ghostty/config; this only
    # adds the themes/ subpath, so there's no collision.
    xdg.configFile."ghostty/themes/dead-world".source = ../../../ghostty/themes/dead-world;

    programs.ghostty = {
        enable = true;
        # useGlobalPkgs is on, so this uses the system nixpkgs (nixos-unstable).
        enableBashIntegration = true;

        settings = {
            # Mirror the alacritty look-and-feel (see utils/alacritty/alacritty.toml).
            font-family = "monospace";
            font-size = 12;

            cursor-style = "block";
            cursor-style-blink = true;

            window-padding-x = 8;
            window-padding-y = 8;
            # Match alacritty: dead-world's #0e1614 background (from the theme) at 0.85 opacity.
            background-opacity = 0.85;

            scrollback-limit = 10000000; # bytes (~10MB), rough parity with alacritty's 10k lines

            # OSC 52 clipboard access, matching alacritty's `osc52 = "CopyPaste"`.
            clipboard-read = "allow";
            clipboard-write = "allow";

            # ghostty sets TERM=xterm-ghostty, which remote hosts don't know, breaking
            # ssh sessions ("can't find terminal definition for xterm-ghostty").
            # ssh-terminfo installs the terminfo on the remote on first connect;
            # ssh-env falls back to TERM=xterm-256color where it can't. Defaults for
            # the other features (cursor,title,path on; sudo off) are preserved.
            shell-integration-features = "cursor,title,path,ssh-env,ssh-terminfo";

            # Send ESC+CR on Shift+Return for multiline input in TUIs, matching the
            # alacritty keyboard binding.
            keybind = [
                "shift+enter=text:\\x1b\\r"
            ];

            theme = "dead-world";
        };
    };
}
