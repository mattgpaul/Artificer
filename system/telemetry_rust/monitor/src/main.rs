use std::thread;
use std::time::Duration;

mod models;
mod traits;
use models::cpu::Cpu;
use crate::traits::telemetry::Telemetry;

// ticks in ms
const TICK: u64 = 1000;
fn main() {
    let mut cpu = Cpu::new();

    // Main loop
    loop {
        cpu.refresh();
        println!("{}", cpu.get_core_usage(1));
        //sleep
        thread::sleep(Duration::from_millis(TICK));
    }
}

