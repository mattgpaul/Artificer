use std::fs;

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
    pub fn read_from_proc_stat(&mut self) -> bool {
        // read from file
        let contents = fs::read_to_string("/proc/stat");
        //process lines
        println!("{:?}", contents);
        true
    }
}