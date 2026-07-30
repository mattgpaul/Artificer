{
    description = "Artificer — NixOS hosts, shared dev shells, and deployable packages";

    inputs = {
        nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
        home-manager = {
            url = "github:nix-community/home-manager";
            inputs.nixpkgs.follows = "nixpkgs";
        };
        flake-utils.url = "github:numtide/flake-utils";

        # Python-from-uv packaging stack. Dormant until a `uv.lock` exists at the
        # repo root (see the `pythonPackages` guard below), so these only cost an
        # entry in flake.lock until Python packaging is actually used.
        pyproject-nix = {
            url = "github:pyproject-nix/pyproject.nix";
            inputs.nixpkgs.follows = "nixpkgs";
        };
        uv2nix = {
            url = "github:pyproject-nix/uv2nix";
            inputs.pyproject-nix.follows = "pyproject-nix";
            inputs.nixpkgs.follows = "nixpkgs";
        };
        pyproject-build-systems = {
            url = "github:pyproject-nix/build-system-pkgs";
            inputs.pyproject-nix.follows = "pyproject-nix";
            inputs.uv2nix.follows = "uv2nix";
            inputs.nixpkgs.follows = "nixpkgs";
        };
    };

    outputs = {
        self,
        nixpkgs,
        ...
    }@inputs:
    let
        lib = nixpkgs.lib;

        # -------------------------------------------------------------------
        # NixOS hosts — the root flake's original responsibility, unchanged.
        # -------------------------------------------------------------------
        mkHost = hostModule:
        nixpkgs.lib.nixosSystem {
            specialArgs = { inherit inputs; };
            modules = [
                ./utils/nixos/common.nix
                    hostModule
            ];
        };

        hosts = {
            nixosConfigurations = {
                sevro = mkHost ./utils/nixos/hosts/sevro/sevro.nix;
                cerebro = mkHost ./utils/nixos/hosts/cerebro/cerebro.nix;
                swordfish = mkHost ./utils/nixos/hosts/swordfish/swordfish.nix;
            };
        };

        # -------------------------------------------------------------------
        # Per-system dev shells + packages. This block is a FIXED skeleton:
        # Rust members are discovered from the Cargo workspace, Python members
        # from the uv workspace. Adding a project means editing a `members`
        # list (or dropping in a package.nix), never this file.
        # -------------------------------------------------------------------
        perSystem = inputs.flake-utils.lib.eachDefaultSystem (system:
        let
            pkgs = import nixpkgs { inherit system; };
            python = pkgs.python312;

            # ---- Rust: one package per Cargo workspace member ----
            # Reads members straight out of the root Cargo.toml, then reads each
            # member's own Cargo.toml for its crate name. Dormant until the root
            # Cargo.lock exists (run `cargo generate-lockfile` once).
            rustPackages =
                lib.optionalAttrs
                    (builtins.pathExists ./Cargo.toml && builtins.pathExists ./Cargo.lock)
                    (let
                        workspace = builtins.fromTOML (builtins.readFile ./Cargo.toml);
                        crateName = member:
                            (builtins.fromTOML
                                (builtins.readFile (./. + "/${member}/Cargo.toml"))).package.name;
                        mkCrate = member:
                            let name = crateName member; in
                            lib.nameValuePair name (pkgs.rustPlatform.buildRustPackage {
                                pname = name;
                                version = "0.1.0";
                                src = ./.;
                                cargoLock.lockFile = ./Cargo.lock;
                                cargoBuildFlags = [ "--package" name ];
                                # Packaging is a deploy build, not a test run. The
                                # workspace intentionally carries red-phase (`todo!()`)
                                # tests from the /tdd workflow; run tests in the dev
                                # shell / CI (`cargo test -p <name>`), not here.
                                doCheck = false;
                            });
                    in
                        builtins.listToAttrs (map mkCrate workspace.workspace.members));

            # ---- Python: one package per uv workspace member ----
            # Mirrors the Rust block: reads members straight out of the root
            # pyproject.toml, then each member's own pyproject.toml for its
            # project name, and builds a per-member virtualenv exposing that
            # member's console scripts. Adding a project means listing it in the
            # root pyproject.toml, never editing this file. Dormant until the
            # root uv.lock exists (run `uv lock` once).
            pythonPackages =
                lib.optionalAttrs
                    (builtins.pathExists ./pyproject.toml && builtins.pathExists ./uv.lock)
                    (let
                        workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
                            workspaceRoot = ./.;
                        };
                        overlay = workspace.mkPyprojectOverlay { sourcePreference = "wheel"; };
                        pythonSet =
                            (pkgs.callPackage inputs.pyproject-nix.build.packages {
                                inherit python;
                            }).overrideScope (lib.composeManyExtensions [
                                inputs.pyproject-build-systems.overlays.default
                                overlay
                            ]);
                        members =
                            (builtins.fromTOML
                                (builtins.readFile ./pyproject.toml)).tool.uv.workspace.members;
                        projName = member:
                            (builtins.fromTOML
                                (builtins.readFile (./. + "/${member}/pyproject.toml"))).project.name;
                        mkPyApp = member:
                            let
                                name = projName member;
                                env = pythonSet.mkVirtualEnv "${name}-env" { ${name} = [ ]; };
                            in
                            lib.nameValuePair name (env // {
                                meta = (env.meta or {}) // { mainProgram = name; };
                            });
                    in
                        builtins.listToAttrs (map mkPyApp members));
        in
        {
            # Shared, reusable dev shells. Projects select one from their .envrc:
            #   use flake "$(git rev-parse --show-toplevel)#rust"
            devShells.rust = pkgs.mkShell {
                buildInputs = with pkgs; [ rustc cargo clippy rustfmt rust-analyzer ];
            };

            devShells.python = pkgs.mkShell {
                buildInputs = [ python pkgs.uv ];
                shellHook = ''
                    export UV_PYTHON_PREFERENCE=only-system
                    export UV_PYTHON=${python}/bin/python
                '';
            };

            # Deployable artifacts. NixOS hosts reference these as
            #   self.packages.''${system}.<name>
            packages = rustPackages // pythonPackages;
        });
    in
    hosts // perSystem;
}
