# Raspberry Pi 3 Base Image (SIL)

This package provides a **minimal ARM64 Debian userland** container image intended
to approximate a Raspberry Pi 3 running a Debian-family OS (CPU/distro parity).

It is **not** hardware emulation (no GPIO/I2C/SPI/VideoCore).

## Build + load into Docker

```bash
bazel run //infrastructure/raspberry_pi:pi3_base_image
```

This loads `artificer-pi3-base:latest` into your local Docker daemon.

## Run

```bash
docker run --rm --platform linux/arm64 artificer-pi3-base:latest uname -m
```

Expected output: `aarch64`.

## Running on x86_64 (emulation)

To run `--platform linux/arm64` containers on an x86_64 host, install binfmt/QEMU:

```bash
docker run --privileged --rm tonistiigi/binfmt --install arm64
```

