mod models;
mod traits;
use models::cpu::Cpu;
use crate::traits::telemetry::Telemetry;

fn main() {
    let mut cpu = Cpu::new();

    // Main loop
    cpu.refresh();
    let foo = cpu.get_core_usage();
    for i in (1..4) {
        println!("{}",foo[1])
    }
}

