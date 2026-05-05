use std::fs;
use std::process::Command;
use crate::traits::telemetry::Telemetry;

#[derive(Debug, Clone, PartialEq)]
pub struct Storage {
    pub max_storage: u64,
    pub available_storage: u64,
}

impl Storage {
    pub fn new() -> Option<Self> {
        let mut storage = Storage {
            max_storage: 0,
            available_storage: 0,
        };
        storage.set_max_storage();
        storage.get_available_storage();
        Some(storage)
    }

    fn set_max_storage(&mut self) {
        if let Some(bytes) = read_root_disk_bytes() {
            self.max_storage = bytes;
        }
    }

    fn get_available_storage(&mut self) {
        if let Some(bytes) = df_available_bytes() {
            self.available_storage = bytes;
        }
    }
}

impl Telemetry for Storage {
    fn refresh(&mut self) {
        self.get_available_storage();
    }
}

// Reads /proc/mounts to find the block device mounted at "/".
fn read_root_device() -> Option<String> {
    let contents = fs::read_to_string("/proc/mounts").ok()?;
    for line in contents.lines() {
        let mut parts = line.split_whitespace();
        let device = parts.next()?;
        let mount = parts.next()?;
        if mount == "/" && device.starts_with("/dev/") {
            return Some(device.trim_start_matches("/dev/").to_string());
        }
    }
    None
}

// nvme1n1p2 -> nvme1n1, sda1 -> sda
fn partition_parent(partition: &str) -> String {
    if let Some(pos) = partition.rfind('p') {
        if partition[pos + 1..].chars().all(|c| c.is_ascii_digit()) {
            return partition[..pos].to_string();
        }
    }
    partition.trim_end_matches(|c: char| c.is_ascii_digit()).to_string()
}

// Total partition size from /sys/block/<parent>/<partition>/size (512-byte sectors).
fn read_root_disk_bytes() -> Option<u64> {
    let partition = read_root_device()?;
    let parent = partition_parent(&partition);
    let path = format!("/sys/block/{}/{}/size", parent, partition);
    let sectors: u64 = fs::read_to_string(path).ok()?.trim().parse().ok()?;
    Some(sectors * 512)
}

// Available bytes from `df -B1`, avoiding human-readable locale-dependent output.
fn df_available_bytes() -> Option<u64> {
    let device = format!("/dev/{}", read_root_device()?);
    let output = Command::new("df")
        .args(["-B1", &device])
        .output()
        .ok()?;
    if !output.status.success() {
        eprintln!("Warning: df exited with status {}", output.status);
        return None;
    }
    let stdout = String::from_utf8(output.stdout).ok()?;
    let data_line = stdout.lines().nth(1)?;
    data_line.split_whitespace().nth(3)?.parse().ok()
}
