use std::{fs, io::Read};
use std::path::PathBuf;
use num_cpus;
use super::cpu_core::CpuCoreTelemetry;
use crate::traits::telemetry::{Telemetry};

// Structure definitions
#[derive(Debug, Clone, PartialEq)]
pub struct Cpu {
    pub vendor_name: String,
    pub model_name: String,
    pub max_freq: f64,
    pub temp_deg_c: f64,
    pub cores: Vec<CpuCoreTelemetry>,
    tctl_path: PathBuf,
}

impl Cpu {
    pub fn new() -> Option<Self> {
        let num_cores = num_cpus::get();
        let mut cores = Vec::with_capacity(num_cores);
        for i in 0..num_cores {
            cores.push(CpuCoreTelemetry::new(i));
        }
        // get the cpu hwmon path
        let tctl_path = Self::get_tctl_path()?;

        let mut cpu = Cpu {
                    vendor_name: "N/A".to_string(),
                    model_name: "N/A".to_string(),
                    max_freq: 0.0,
                    temp_deg_c: 0.0,
                    cores,
                    tctl_path,
        };
        cpu.get_cpu_vendor_info();
        cpu.get_max_freq();
        cpu.get_cpu_temp();
        Some(cpu)
    }
    //get cpu data
    fn get_cpu_vendor_info(&mut self) {
        const CPUINFO: &str = "/proc/cpuinfo";
        let cpuinfo = match fs::read_to_string(CPUINFO) {
            Ok(s) => s,
            Err(e) => {
                eprintln!("Warning: could not read {CPUINFO}: {e}");
                return;
            }
        };
        let mut found_vendor = false;
        let mut found_model = false;
        for line in cpuinfo.lines() {
            if !found_vendor && line.starts_with("vendor_id") {
                if let Some(v) = line.split_whitespace().nth(2) {
                    self.vendor_name = v.to_string();
                    found_vendor = true;
                }
            } else if !found_model && line.starts_with("maodel name") {
                self.model_name = line.split_whitespace()
                    .skip(3)
                    .collect::<Vec<_>>()
                    .join(" ");
                found_model = true;
            }
            if found_vendor && found_model {
                break; // all cores identical
            }
        }
    }
    // get max frequency of the cpu
    fn get_max_freq(&mut self) {
        const FREQPATH: &str = "/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq";
        match fs::read_to_string(FREQPATH) {
            Ok(freq) => {
                if let Ok(val) = freq.trim().parse::<f64>() {
                    self.max_freq = val / 1000.0;
                }
            }
            Err(e) => eprintln!("Warning: could not read max freq: {e}"),
        }
    }
    // get k10temp path
    fn get_k10temp_path() -> Option<PathBuf> {
        const HWMON_PATH: &str = "/sys/class/hwmon/";
        const K10TEMP_NAME: &[u8] = b"k10temp";
        let hwmon_dir = fs::read_dir(HWMON_PATH).ok()?;
        let mut buf = [0u8; 8];

        for dir_entry in hwmon_dir {
            let Ok(dir_entry) = dir_entry else { continue };
            let path = dir_entry.path();

            let Ok(mut f) = fs::File::open(path.join("name")) else { continue };
            let _ = f.read_exact(&mut buf);

            if buf.starts_with(K10TEMP_NAME) {
                return Some(path);
            }
        }
        None
    }
    // get the tctl path for temp updates
    fn get_tctl_path() -> Option<PathBuf> {
        const TEMP_LABEL: &[u8] = b"Tctl";
        let k10path = Self::get_k10temp_path()?;
        let hwmon_dir = fs::read_dir(k10path).ok()?;
        let mut buf = [0u8; 8];

        for dir_entry in hwmon_dir {
            let Ok(dir_entry) = dir_entry else { continue };
            let path = dir_entry.path();

            let Ok(mut f) = fs::File::open(&path) else { continue };
            let _ = f.read_exact(&mut buf);

            if buf.starts_with(TEMP_LABEL) {
                // need to replace "*label" with "*input" then return
                let file_name = path.file_name()?;
                let file_name = file_name.to_str()?;
                let file_name = file_name.replace("label", "input");
                let new_path = path.with_file_name(file_name);
                return Some(new_path);
            }
        }
        None
    }
    // get cpu temp
    fn get_cpu_temp(&mut self) {
        if let Ok(temp) = fs::read_to_string(&self.tctl_path) {
            if let Ok(val) = temp.trim().parse::<f64>() {
                self.temp_deg_c = val / 1000.0;
            }
        }
    }
    // get core usage
}

impl Telemetry for Cpu {
    fn refresh(&mut self) {
        if let Ok(contents) = fs::read_to_string("/proc/stat") {
            for core in self.cores.iter_mut() {
                core.update_from_stat(&contents);
            }
        }
        self.get_cpu_temp();
    }
}