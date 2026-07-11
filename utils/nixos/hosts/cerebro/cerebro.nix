{ config, lib, pkgs, ... }:
let
    # llama.cpp built against ROCm for the RX 7900 XTX (gfx1100).
    llamaRocm = pkgs.llama-cpp.override {
        rocmSupport = true;
        rocmGpuTargets = [ "gfx1100" ];
    };

    # Shorthand launcher (like an old `make`/`task` target, but on $PATH and
    # reproducible). Serves Gemma 3 27B fully on the GPU at 32k context with
    # 8-bit KV cache, and --jinja on for tool calling from opencode.
    # Extra args pass through, e.g. `llama-gemma --port 9090`.
    llama-gemma = pkgs.writeShellScriptBin "llama-gemma" ''
        exec ${llamaRocm}/bin/llama-server \
            -hf ggml-org/gemma-3-27b-it-GGUF \
            --alias gemma-3-27b \
            -ngl 99 -fa on \
            --ctx-size 65536 \
            --cache-type-k q8_0 --cache-type-v q8_0 \
            --jinja \
            --host 127.0.0.1 --port 8080 \
            "$@"
    '';

    # Coder model for opencode: Qwen3-Coder 30B-A3B (MoE, ~3B active -> fast,
    # strong native tool-calling). Weights are ~18.6 GB, so context is capped
    # at 32k to leave KV headroom on the 24 GB card. Own port so it coexists
    # with llama-gemma. `llama-coder [extra args]`.
    llama-coder = pkgs.writeShellScriptBin "llama-coder" ''
        exec ${llamaRocm}/bin/llama-server \
            -hf unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:Q4_K_M \
            --alias qwen3-coder \
            -ngl 99 -fa on \
            --ctx-size 32768 \
            --cache-type-k q8_0 --cache-type-v q8_0 \
            --jinja \
            --host 127.0.0.1 --port 8081 \
            "$@"
    '';
in
{
    imports = [
        ./hardware-configuration.nix
        ../../profiles/gaming.nix
        ../../users/admin/system.nix
        ../../users/matthew/system.nix
        ../../users/matthew/home.nix
    ];

    networking.hostName = "cerebro";

    # Cache sudo credentials for 2 hours before re-prompting.
    security.sudo.extraConfig = ''
        Defaults timestamp_timeout=120
    '';

    boot.loader.systemd-boot.enable = true;
    boot.loader.efi.canTouchEfiVariables = true;
    boot.initrd.kernelModules = [ "amdgpu" ];

# may not need AMD drivers, documentation says they work out of the box
# GPU acceleration just needs to be enabled apparently
    
    hardware.graphics = {
            enable = true;
            enable32Bit = true;
        };

    # ROCm compute for llama.cpp on the RX 7900 XTX (gfx1100).
    # gfx1100 is officially supported, so no HSA_OVERRIDE_GFX_VERSION is needed.
    users.users.matthew.extraGroups = [ "render" "video" ];

    environment.systemPackages = with pkgs; [
        llamaRocm                # llama-cli / llama-server (ROCm)
        llama-gemma              # serve Gemma 3 27B (chat) on :8080
        llama-coder              # serve Qwen3-Coder 30B (opencode) on :8081
        rocmPackages.rocminfo    # GPU diagnostics: `rocminfo | grep gfx`
        rocmPackages.rocm-smi    # CLI metrics: `watch -n1 rocm-smi`
        amdgpu_top               # live TUI: VRAM, GPU%, power, per-process
        opencode                 # AI coding agent; points at llama-server /v1
        rustc
        cargo
    ];

    system.stateVersion = "26.05";
}
