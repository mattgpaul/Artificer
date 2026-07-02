{
	description = "Matthew's NixOS systems";
	
	inputs = {
		nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
	};

	outputs = { self, nixpkgs }: {
		nixosConfigurations.sevro = nixpkgs.lib.nixosSystem {
			modules = [
				./common.nix
				./hosts/sevro.nix
			];
		};
	};
}
