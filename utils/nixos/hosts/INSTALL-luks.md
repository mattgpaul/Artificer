# NixOS encrypted install (LUKS2 + btrfs + hibernate)

Encrypted variant of [`INSTALL.md`](./INSTALL.md): **UEFI, full-disk wipe, LUKS2 whole-disk
encryption, btrfs subvolumes, and an encrypted swapfile sized for hibernate.**

Layout produced:
```
DISK
├─ p1  ESP (fat32, 2 GiB, /boot)        ← unencrypted; required to boot
└─ p2  LUKS2 container  ──► cryptroot ──► btrfs (label nixos)
                                           ├─ @      → /
                                           ├─ @home  → /home
                                           ├─ @nix   → /nix
                                           └─ @swap  → /swap   (holds /swap/swapfile)
```
One passphrase at boot unlocks the container; `/`, `/home`, `/nix`, and swap all live inside it,
so the swapfile is persistently keyed and hibernate can resume from it.

Placeholders: `DISK` (swordfish = `/dev/nvme0n1`) and `SWAPSIZE` (swordfish = `64g`; rule for
hibernate is **swap ≥ RAM**, and swordfish has 62 GiB RAM).

> **⚠️ This wipes the disk.** Complete your backups first (`~/.ssh` at minimum) and commit/push
> any dirty repos. Nothing here is reversible.

## 0. Boot the live USB, become root
```bash
sudo -i
lsblk          # identify the target disk -> this is DISK, e.g. /dev/nvme0n1
```
> **Partition suffix gotcha:** NVMe = `DISKp1`, `DISKp2`... (e.g. `/dev/nvme0n1p1`).
> SATA/SSD = `DISK1`, `DISK2`... Substitute accordingly below.

## 0.5. Connect to WiFi (skip if on ethernet)
Same as [`INSTALL.md`](./INSTALL.md) step 0.5 — `nmtui` on the graphical ISO.

## 1. Partition (GPT: ESP + LUKS)
```bash
parted /dev/DISK -- mklabel gpt
parted /dev/DISK -- mkpart ESP fat32 1MiB 2GiB
parted /dev/DISK -- set 1 esp on
parted /dev/DISK -- mkpart cryptroot 2GiB 100%
```
ESP bumped to **2 GiB** (vs 1 GiB in the plain install) — NixOS stores a kernel + initrd per
retained generation in `/boot`, and 1 GiB gets tight.

## 2. Create + open the LUKS2 container
```bash
cryptsetup luksFormat --type luks2 /dev/DISKp2      # type YES, then set the BOOT passphrase
cryptsetup open      /dev/DISKp2 cryptroot          # unlocks -> /dev/mapper/cryptroot
```
> This passphrase is what you type at every boot. Choose a strong one — if lost, the data is
> unrecoverable (that's the point). You can add a TPM auto-unlock and a printed recovery key
> **later**, without reformatting.

## 3. Format ESP + btrfs, create subvolumes
```bash
mkfs.fat -F 32 -n boot /dev/DISKp1                  # ESP
mkfs.btrfs -L nixos    /dev/mapper/cryptroot        # btrfs INSIDE the LUKS container

mount /dev/mapper/cryptroot /mnt
btrfs subvolume create /mnt/@
btrfs subvolume create /mnt/@home
btrfs subvolume create /mnt/@nix
btrfs subvolume create /mnt/@swap
umount /mnt
```

## 4. Mount subvolumes
```bash
mount -o subvol=@,compress=zstd,noatime     /dev/mapper/cryptroot /mnt
mkdir -p /mnt/{home,nix,swap,boot}
mount -o subvol=@home,compress=zstd,noatime /dev/mapper/cryptroot /mnt/home
mount -o subvol=@nix,compress=zstd,noatime  /dev/mapper/cryptroot /mnt/nix
mount -o subvol=@swap,noatime               /dev/mapper/cryptroot /mnt/swap   # NO compress
mount /dev/disk/by-label/boot /mnt/boot
```
> `@swap` is mounted **without** compression — a swapfile must be uncompressed and copy-on-write
> disabled (handled in the next step).

## 5. Create the hibernate swapfile (nocow, ≥ RAM)
Preferred (btrfs-progs ≥ 6.1, present on recent ISOs):
```bash
btrfs filesystem mkswapfile --size SWAPSIZE /mnt/swap/swapfile   # e.g. 64g
swapon /mnt/swap/swapfile
```
Fallback (older ISO without `mkswapfile`):
```bash
truncate -s 0 /mnt/swap/swapfile
chattr +C    /mnt/swap/swapfile        # disable copy-on-write BEFORE writing data
fallocate -l SWAPSIZE /mnt/swap/swapfile
chmod 600    /mnt/swap/swapfile
mkswap       /mnt/swap/swapfile
swapon       /mnt/swap/swapfile
```

## 6. Record three values for the config
Write these down — they go into the flake:
```bash
btrfs inspect-internal map-swapfile -r /mnt/swap/swapfile   # -> RESUME_OFFSET (a number)
cryptsetup luksUUID /dev/DISKp2                             # -> LUKS_UUID
blkid /dev/mapper/cryptroot                                 # -> BTRFS_UUID (UUID=...)
```
- `RESUME_OFFSET` — physical offset of the swapfile; hibernate needs it.
- `LUKS_UUID` — the encrypted partition, for `initrd.luks.devices`.
- `BTRFS_UUID` — the filesystem that holds the swapfile, for `resumeDevice`.

## 7. Generate hardware config
```bash
nixos-generate-config --root /mnt
```
Writes `/mnt/etc/nixos/hardware-configuration.nix`. With everything mounted as above it detects:
the btrfs `fileSystems` (with `subvol=`/`compress=` options), the `boot.initrd.luks.devices."cryptroot"`
entry, and usually the `swapDevices` swapfile. **This is the file you copy into the repo.**
Open it and confirm those three things are present:
```nix
boot.initrd.luks.devices."cryptroot".device = "/dev/disk/by-uuid/LUKS_UUID";
fileSystems."/"     = { fsType = "btrfs"; options = [ "subvol=@" "compress=zstd" "noatime" ]; ... };
fileSystems."/home" = { ... "subvol=@home" ... };
fileSystems."/nix"  = { ... "subvol=@nix" ... };
fileSystems."/swap" = { ... "subvol=@swap" ... };
swapDevices = [ { device = "/swap/swapfile"; } ];
```
If any are missing (the swapfile entry sometimes is), add them by hand.

## 8. Minimal install to get a bootable base
```bash
nixos-install         # prompts for a root password at the end
reboot
```
On reboot you are prompted for the **LUKS passphrase first**, then the root login.

## 9. Boot into the new system -> apply the flake
```bash
# log in, connect to WiFi (nmtui), then:
git clone <your-repo> Artificer
cd Artificer

# copy the generated hardware config into the repo:
cp /etc/nixos/hardware-configuration.nix utils/nixos/hosts/swordfish/hardware-configuration.nix

sudo nixos-rebuild switch --flake .#swordfish
```

## 10. Add the hibernate/resume settings to the flake
`nixos-generate-config` handles LUKS unlock + filesystems + swap, but it does **not** add the
resume pointer. Put this in `hosts/swordfish/swordfish.nix` (the flake replaces
`configuration.nix`, so these must live in the flake), using the values from step 6:
```nix
# --- hibernate (swap ≥ RAM, encrypted swapfile inside the LUKS container) ---
boot.resumeDevice = "/dev/disk/by-uuid/BTRFS_UUID";
boot.kernelParams = [ "resume_offset=RESUME_OFFSET" ];
```
Rebuild, then test: `systemctl hibernate` — the machine powers fully off and, on next boot, after
the LUKS prompt, resumes your session.
> If resume is flaky, add `boot.initrd.systemd.enable = true;` (more robust LUKS-then-resume ordering).
> To hibernate on lid-close/idle, adjust `services.logind` / `hypridle` later — a config tweak, no wipe.

## Why this lines up with the flake config
- **Boot:** host `.nix` sets `systemd-boot` + `canTouchEfiVariables`; the unencrypted ESP at
  `/boot` is what it expects. The LUKS passphrase prompt happens in the initrd, before `/` mounts.
- **Encryption:** `boot.initrd.luks.devices."cryptroot"` (in the generated hardware config) unlocks
  the container early; a single passphrase brings up `/`, `/home`, `/nix`, and swap together.
- **Hibernate:** swap ≥ RAM and lives inside the LUKS container, so it is persistently keyed;
  `resumeDevice` + `resume_offset` let the initrd resume after unlocking.
- **Filesystems:** the generated file provides the btrfs subvolume `fileSystems` by UUID, which is
  why the `./hardware-configuration.nix` import resolves.
- Copy **only** `hardware-configuration.nix`, not `configuration.nix`.

## Add-later, no wipe required
- **TPM2 auto-unlock** (`systemd-cryptenroll --tpm2-device=auto`) — unlock without typing the
  passphrase, while still requiring it if the drive is moved to another machine.
- **Recovery key / extra passphrases** (`cryptsetup luksAddKey`) — print one, store it safely.
- **btrfs snapshots** (snapper/btrbk) of `@home` etc. — the data time-travel that NixOS
  generations do *not* give you.
- **Secure Boot** (evil-maid hardening).

## BIOS reminders (physical, before install)
- **Disable Secure Boot** (systemd-boot won't boot with it on; re-enable only via lanzaboote later).
- Confirm **UEFI mode**, not Legacy/CSM.
