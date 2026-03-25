use num_cpus;
use std::{fs, path::PathBuf};
use std::mem::swap;

use crate::traits::telemetry::{Telemetry, Thermal};

// Structure definitions

#[derive(Debug)]
struct CpuCoreTelemetry {
    core_num: usize,
    usage: u64,
    user: u64,
    nice: u64,
    system: u64,
    idle: u64,
    iowait: u64,
    irq: u64,
    softirq: u64,
    steal: u64,
    guest: u64,
    guest_nice: u64,
}

#[derive(Debug)]
pub struct Cpu {
    hwmon_path: PathBuf,
    temp_deg_c: u64,
    cores: Vec<CpuCoreTelemetry>,
}

// Implementation blocks

impl CpuCoreTelemetry {
    fn new(core_num: usize) -> Self {
        CpuCoreTelemetry { 
            core_num, 
            usage: 0,
            user: 0, 
            nice: 0, 
            system: 0, 
            idle: 0,
            iowait: 0,
            irq: 0,
            softirq: 0,
            steal: 0,
            guest: 0,
            guest_nice: 0,
        }
    }
    // Read from proc stat
    //TODO: compensate for windows (*blegh*)
    fn read_from_proc_stat(&mut self) -> Result<(), std::io::Error>{
        // read from file
        let contents = fs::read_to_string("/proc/stat")?;
        //process lines
        let lines: Vec<&str> = contents.lines().collect();
        for line in lines {
            if line.starts_with(&format!("cpu{}", self.core_num)) {
                let parts: Vec<&str> = line.split_whitespace().collect();
                
                self.user = parts[1].parse::<u64>().unwrap();
                self.nice = parts[2].parse::<u64>().unwrap();
                self.system = parts[3].parse::<u64>().unwrap();
                self.idle = parts[4].parse::<u64>().unwrap();
                self.iowait = parts[5].parse::<u64>().unwrap();
                self.irq = parts[6].parse::<u64>().unwrap();
                self.softirq = parts[7].parse::<u64>().unwrap();
                self.steal = parts[8].parse::<u64>().unwrap();
                self.guest = parts[9].parse::<u64>().unwrap();
                self.guest_nice = parts[10].parse::<u64>().unwrap();
            }
        }
        Ok(())
    }
    // calculate total time
    fn get_total_time(&self) -> u64 {
        self.user + self.nice + self.system + self.idle + self.iowait + self.irq + self.softirq + self.steal + self.guest + self.guest_nice
    }
    fn get_idle_time(&self) -> u64 {
        self.idle + self.iowait 
    }
    // calculate core usage based on time delta
}

impl Telemetry for CpuCoreTelemetry {
    fn refresh(&mut self) {
        let previous_total = self.get_total_time();
        let previous_idle = self.get_idle_time();
        // refresh the usage times
        let _ = self.read_from_proc_stat();
        let current_total = self.get_total_time();
        let current_idle = self.get_idle_time();
        // calculate deltas
        let delta_total = current_total - previous_total;
        let delta_idle = current_idle - previous_idle;
        // calculate the usage 
        self.usage = if delta_total > 0 {
            let numerator = (delta_total - delta_idle) * 100;
            (numerator + delta_total / 2) / delta_total
        } else {
            0
        };
    }
}


impl Cpu {
    pub fn new() -> Self {
        let num_cores = num_cpus::get();
        let mut cores = Vec::with_capacity(num_cores);
        for i in 0..num_cores {
            cores.push(CpuCoreTelemetry::new(i));
        }
        // get the cpu hwmon path
        let hwmon_path = Self::get_hwmon_path();

        Cpu {
            hwmon_path,
            temp_deg_c: 0,
            cores,
        }
    }
    // get core usage
    pub fn get_core_usage(&self, core_num: usize) -> &u64 {
        &self.cores[core_num].usage
    }
    // find hwmon for cpu
// src/models/cpu.rs
    fn get_hwmon_path() -> PathBuf {
        let path = PathBuf::from("/sys/class/hwmon");
        
        // iterate through all hwmon directories
        if let Ok(entries) = fs::read_dir(&path) {
            for entry in entries {
                if let Ok(entry) = entry {
                    let entry_path = entry.path();
                    // Check if this is a directory
                    if entry_path.is_dir() {
                        // Try to read the name file in this directory
                        let name_path = entry_path.join("name");
                        if let Ok(name_content) = fs::read_to_string(&name_path) {
                            // check if the name contains "k10temp"
                            if name_content.trim().contains("k10temp") {
                                println!("hwmon path: {:?}", entry_path);
                                return entry_path;
                            }
                        }
                    }
                }
            }
        }
        
        // Return default path if no k10temp device found
        path
    }
}

impl Thermal for Cpu {
    fn get_temperature(&mut self) {

    }
}

impl Telemetry for Cpu {
    fn refresh(&mut self) {
        // refresh all cores
        for core in self.cores.iter_mut() {
            core.refresh();
        }
    }
}

// thermal telemetry