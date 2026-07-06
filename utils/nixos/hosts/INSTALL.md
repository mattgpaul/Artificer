# NixOS manual install (barebones → flake rebuild)

Reference for flashing a host manually: **UEFI, ext4, full-disk wipe, with a swap partition.**
Placeholders: `DISK` (e.g. `/dev/nvme0n1`) and `SWAP_END`.

## 0. Boot the live USB, become root
```bash
sudo -i
lsblk          # identify the target disk -> this is DISK, e.g. /dev/nvme0n1
```
> **Partition suffix gotcha:** NVMe = `DISKp1`, `DISKp2`... (e.g. `/dev/nvme0n1p1`).
> SATA/SSD = `DISK1`, `DISK2`... (e.g. `/dev/sda1`). Substitute accordingly below.

## 0.5. Connect to WiFi (skip if on ethernet)

NetworkManager is running on the graphical ISO. Use the TUI:
```bash
nmtui
# Activate a connection -> pick your network -> enter password
```

On the **minimal ISO** (no NetworkManager), use wpa_supplicant directly:
```bash
ip link                                                  # find interface name, e.g. wlp13s0
wpa_passphrase "YourSSID" "YourPassword" > /tmp/wifi.conf
wpa_supplicant -B -i wlp13s0 -c /tmp/wifi.conf
dhcpcd wlp13s0
```

> Credentials do **not** carry over to the installed system. You will need to connect again
> in step 6 after first boot — use `nmtui` there too.

## 1. Partition (GPT: ESP + swap + root)
```bash
parted /dev/DISK -- mklabel gpt
parted /dev/DISK -- mkpart ESP fat32 1MiB 1GiB
parted /dev/DISK -- set 1 esp on
parted /dev/DISK -- mkpart swap linux-swap 1GiB SWAP_END      # e.g. 17GiB for 16G swap
parted /dev/DISK -- mkpart root ext4 SWAP_END 100%
```
`SWAP_END` = `1GiB + swap size`. For 16G swap -> `17GiB`. For 32G (hibernate) -> `33GiB`.

## 2. Format
```bash
mkfs.fat -F 32 -n boot /dev/DISKp1     # ESP
mkswap  -L swap        /dev/DISKp2
mkfs.ext4 -L nixos     /dev/DISKp3
```

## 3. Mount + enable swap
```bash
mount /dev/disk/by-label/nixos /mnt
mkdir -p /mnt/boot
mount /dev/disk/by-label/boot /mnt/boot
swapon /dev/DISKp2
```

## 4. Generate hardware config
```bash
nixos-generate-config --root /mnt
```
Writes `/mnt/etc/nixos/hardware-configuration.nix` — auto-detects `fileSystems`, the
`swapDevices` entry, and boot kernel modules. **This is the file you copy into the repo.**

## 5. Minimal install to get a bootable base
```bash
nixos-install          # uses the generated configuration.nix; installs base system
                       # prompts for a root password at the end
reboot
```

## 6. Boot into the new system -> apply the flake
```bash
# log in, connect to WiFi if needed (see step 0.5 — same nmtui command applies here),
# then:
git clone <your-repo> Artificer
cd Artificer

# copy the generated hardware config into the repo where <host>.nix imports it:
cp /etc/nixos/hardware-configuration.nix utils/nixos/hosts/<host>/hardware-configuration.nix

sudo nixos-rebuild switch --flake .#<host>
```

## Why this lines up with the flake config
- **Boot:** host `.nix` sets `systemd-boot` + `canTouchEfiVariables`; the ESP mounted at
  `/boot` is exactly what it expects.
- **Swap:** handled entirely by the generated `hardware-configuration.nix` (`swapDevices`) —
  nothing to add to the flake.
- **Filesystems:** the generated file provides `fileSystems."/"` and `fileSystems."/boot"`
  by UUID, which is why the `./hardware-configuration.nix` import resolves.
- Copy **only** `hardware-configuration.nix`, not `configuration.nix` — so there's no
  conflict with the boot/graphics/etc. settings already in the flake.

## BIOS reminders (physical, before install)
- **Disable Secure Boot** (systemd-boot won't boot with it on).
- Confirm **UEFI mode**, not Legacy/CSM.
