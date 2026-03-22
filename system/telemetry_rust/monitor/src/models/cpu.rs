use num_cpus;
use std::fs;
use std::mem::swap;

use crate::traits::telemetry::Telemetry;

// #[derive(Debug)]
struct CpuCoreTelemetry {
    core_num: usize,
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
    fn new(core_num: usize) -> Self {
        CpuCoreTelemetry { core_num, 
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
}

impl Telemetry for CpuCoreTelemetry {
    fn refresh(&mut self) {
        let _ = self.read_from_proc_stat();
    }
}

// #[derive(Debug)]
struct CpuCoreDelta {
    // Vector of cores at t0
    cores_t0: Vec<CpuCoreTelemetry>,
    // vector of cores at t-1
    cores_tm1: Vec<CpuCoreTelemetry>
}

impl CpuCoreDelta {
    fn new() -> Self {
        let num_cores = num_cpus::get();
        let mut cores_t0 = Vec::with_capacity(num_cores);
        let mut cores_tm1 = Vec::with_capacity(num_cores);

        for i in 0..num_cores {
            cores_t0.push(CpuCoreTelemetry::new(i));
            cores_tm1.push(CpuCoreTelemetry::new(i));
        }

        CpuCoreDelta {
            cores_t0,
            cores_tm1,
        }
    }
    fn calculate_core_usage(&self) -> Vec<u64> {
        let mut usage = vec![0u64; self.cores_t0.len()];
        for (i,_) in self.cores_t0.iter().enumerate() {
            let current_total = self.cores_t0[i].get_total_time();
            let current_idle = self.cores_t0[i].get_idle_time();
            let previous_total = self.cores_tm1[i].get_total_time();
            let previous_idle = self.cores_tm1[i].get_idle_time();
            let delta_total = current_total - previous_total;
            let delta_idle = current_idle - previous_idle;
            
            // Handle zero divisor case
            if delta_total > 0 {
                usage[i] = ((delta_total - delta_idle) / delta_total) * 100;
            } else {
                usage[i] = 0;
            }
        }
        usage
    }
}

impl Telemetry for CpuCoreDelta {
    fn refresh(&mut self) {
        // set t0 to tm1 values
        swap(&mut self.cores_tm1, &mut self.cores_t0);
        // get new core values
        for core in self.cores_t0.iter_mut() {
            core.refresh();
        }
    }
}

// #[derive(Debug)]
pub struct Cpu {
    core_usage_pct: Vec<u64>,
    delta: CpuCoreDelta,
}

impl Cpu {
    pub fn new() -> Self {
        Cpu {
            // initialize a vector of zeros the length of num cpus
            core_usage_pct: vec![0; num_cpus::get()],
            delta: CpuCoreDelta::new(),
        }
    }
    pub fn get_core_usage(&self) -> &[u64] {
        &self.core_usage_pct 
    }
} 

impl Telemetry for Cpu {
    fn refresh(&mut self) {
       self.delta.refresh();
       self.core_usage_pct = self.delta.calculate_core_usage(); 
    }
}