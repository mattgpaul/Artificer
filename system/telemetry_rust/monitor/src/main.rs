mod models;
use models::cpu::CpuCoreTelemetry;

fn main() {
    let mut cpu = CpuCoreTelemetry::new(0);

    // Main loop
    cpu.read_from_proc_stat();
    println!("{:?}", cpu)
}

