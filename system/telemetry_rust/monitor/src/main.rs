mod nodes;

fn main() {
    println!("Starting CPU Telemetry Monitor...");
    
    use nodes::cpu::{CpuMonitor};
    use std::time::Duration;
    
    let mut monitor = CpuMonitor::new();
    
    // Print initial CPU info
    match monitor.update() {
        Ok(cpu_info) => {
            println!("Initial CPU Info:");
            println!("  CPU Usage: {:.2}%", cpu_info.cpu_usage);
            println!("  Load Average: {:.2}, {:.2}, {:.2}",
                     cpu_info.load_average[0],
                     cpu_info.load_average[1],
                     cpu_info.load_average[2]);
            println!("  CPU Count: {}", cpu_info.cpu_count);
        }
        Err(e) => {
            eprintln!("Error getting initial CPU info: {}", e);
        }
    }
    
    // Continuous monitoring loop
    loop {
        std::thread::sleep(Duration::from_secs(2));
        
        match monitor.update() {
            Ok(cpu_info) => {
                println!("CPU Usage: {:.2}% | Load Average: {:.2}, {:.2}, {:.2}",
                         cpu_info.cpu_usage,
                         cpu_info.load_average[0],
                         cpu_info.load_average[1],
                         cpu_info.load_average[2]);
            }
            Err(e) => {
                eprintln!("Error updating CPU info: {}", e);
            }
        }
    }
}
