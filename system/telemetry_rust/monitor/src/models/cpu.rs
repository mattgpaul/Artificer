use std::fs;

#[derive(Debug)]
pub struct CpuCoreTelemetry {
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
    pub fn new(core_num: usize) -> Self {
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
    pub fn read_from_proc_stat(&mut self) -> Result<(), std::io::Error>{
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
}