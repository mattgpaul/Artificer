{
    description = "Matthew's NixOS systems";

    inputs = {
        nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
        home-manager = {
            url = "github:nix-community/home-manager";
            inputs.nixpkgs.follows = "nixpkgs";
        };
    };

    outputs = {
        self, 
        nixpkgs,
        ...
    }@inputs: 
    let
        mkHost = hostModule:
        nixpkgs.lib.nixosSystem {
            specialArgs = { inherit inputs; };
            modules = [
                ./utils/nixos/common.nix
                    hostModule
            ];
        };
    in {
        nixosConfigurations = {
            sevro = mkHost ./utils/nixos/hosts/sevro/sevro.nix;
            cerebro = mkHost ./utils/nixos/hosts/cerebro/cerebro.nix;
        };
    };
}
