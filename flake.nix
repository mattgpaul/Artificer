{
	description = "Matthew's NixOS systems";
	
	inputs = {
		nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
	};

	outputs = { self, nixpkgs }: {
		nixosConfigurations.sevro = nixpkgs.lib.nixosSystem {
			modules = [
				./utils/nixos/common.nix
				./utils/nixos/hosts/sevro.nix
			];
		};
	};
}
