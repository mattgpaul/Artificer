mod models;
mod traits;
use models::cpu::CpuMonitor;
use crate::traits::telemetry::Telemetry;

fn main() {
    let mut cpu = CpuMonitor::new();

    // Main loop
    cpu.refresh();
    println!("{:?}", cpu)
}

