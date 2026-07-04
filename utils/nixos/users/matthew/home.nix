{inputs, pkgs, ... }:
{
    imports = [ inputs.home-manager.nixosModules.default ];

    home-manager.useGlobalPkgs = true;
    home-manager.useUserPackages = true;

    home-manager.users.matthew = {
        home.username = "matthew";
        home.homeDirectory = "/home/matthew";
        home.stateVersion = "26.05";
        programs.home-manager.enable = true;
        programs.bash = {
            enable = true;
        };
        home.packages = with pkgs; [
# packages here
        ];
    };
}
