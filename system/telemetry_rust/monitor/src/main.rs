use std::thread;
use std::time::Duration;

mod models;
mod traits;
use models::cpu::Cpu;
use models::gpu::Gpu;
use models::memory::Memory;
use crate::traits::telemetry::Telemetry;
// ticks in ms
const TICK: u64 = 1000;
fn main() {
    let mut cpu = Cpu::new().expect("Failed to initialize the CPU");
    let mut gpu = Gpu::new();
    let mut memory = Memory::new();
    // Main loop
    loop {
        cpu.refresh();
        gpu.refresh();
        memory.refresh();
        println!("{:?}", memory);
        //sleep
        thread::sleep(Duration::from_millis(TICK));
    }
}

