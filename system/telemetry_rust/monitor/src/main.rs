use std::thread;
use std::time::Duration;

mod models;
mod traits;
use models::cpu::Cpu;
use models::gpu::Gpu;
use crate::traits::telemetry::Telemetry;

// ticks in ms
const TICK: u64 = 1000;
fn main() {
    let mut cpu = Cpu::new().expect("Failed to initialize the CPU");
    let mut gpu = Gpu::new();
    // Main loop
    loop {
        cpu.refresh();
        println!("{:?}", gpu);
        //sleep
        thread::sleep(Duration::from_millis(TICK));
    }
}

