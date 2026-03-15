mod nodes;

use nodes::cpu::CpuTelemetry;

fn main() {
    let mut cpu = CpuTelemetry::new();

    // Main loop
    loop {
        cpu.refresh();
    }
}
