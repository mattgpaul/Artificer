use std::fs;
use std::io::{Error, ErrorKind};

use crate::traits::telemetry::Telemetry;

#[derive(Debug)]
pub struct CpuCoreTelemetry {
    pub core_num: usize,
    pub usage: u64,
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

impl CpuCoreTelemetry {
    pub fn new(core_num: usize) -> Self {
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
                
                self.user = parts[1].parse::<u64>().map_err(|e| Error::new(ErrorKind::InvalidData,e))?;
                self.nice = parts[2].parse::<u64>().map_err(|e| Error::new(ErrorKind::InvalidData,e))?;
                self.system = parts[3].parse::<u64>().map_err(|e| Error::new(ErrorKind::InvalidData,e))?;
                self.idle = parts[4].parse::<u64>().map_err(|e| Error::new(ErrorKind::InvalidData,e))?;
                self.iowait = parts[5].parse::<u64>().map_err(|e| Error::new(ErrorKind::InvalidData,e))?;
                self.irq = parts[6].parse::<u64>().map_err(|e| Error::new(ErrorKind::InvalidData,e))?;
                self.softirq = parts[7].parse::<u64>().map_err(|e| Error::new(ErrorKind::InvalidData,e))?;
                self.steal = parts[8].parse::<u64>().map_err(|e| Error::new(ErrorKind::InvalidData,e))?;
                self.guest = parts[9].parse::<u64>().map_err(|e| Error::new(ErrorKind::InvalidData,e))?;
                self.guest_nice = parts[10].parse::<u64>().map_err(|e| Error::new(ErrorKind::InvalidData,e))?;
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