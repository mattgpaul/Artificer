use std::{fs, io::Read};
use std::path::PathBuf;
use num_cpus;
use super::cpu_core::CpuCoreTelemetry;
use crate::traits::telemetry::{Telemetry};

// Structure definitions
#[derive(Debug)]
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
        const VENDOR: &str = "vendor_id";
        const MODEL: &str = "model name";
        //read in the file
        let cpuinfo = fs::read_to_string(CPUINFO).expect("Failed to read file");
        // loop through the lines to find the vendor
        for line in cpuinfo.lines() {
            if line.starts_with(VENDOR) {
                let parts: Vec<&str> = line.split_whitespace().collect();
                self.vendor_name = parts[2].to_string();
            }
        }
        // repeat for the model
        for line in cpuinfo.lines() {
            if line.starts_with(MODEL) {
                let parts: Vec<&str> = line.split_whitespace().collect();
                self.model_name = parts[3..].join(" ");
            }
        }
    }
    // get max frequency of the cpu
    fn get_max_freq(&mut self) {
        const FREQPATH: &str = "/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq";
        let freq = fs::read_to_string(FREQPATH).expect("Failed to read file");
        self.max_freq = freq.trim().parse::<f64>().expect("Failed to parse float") / 1000.0;
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
        let temp = fs::read_to_string(&self.tctl_path)
            .expect("Failed to read temperature file for cpu");
            self.temp_deg_c = temp.trim().parse::<f64>().expect("Failed to parse float") / 1000.0;
    }
    // get core usage
}

impl Telemetry for Cpu {
    fn refresh(&mut self) {
        // update the core telemetry 
        for core in self.cores.iter_mut() {
            core.refresh();
        }
        self.get_cpu_temp();
    }
}