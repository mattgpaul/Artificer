enum Manufacturer {
    Amd,
    Intel,
    Apple,
}
struct CpuCoreTelemetry {
   core_num: usize,
   temp: f64,
}

pub struct CpuTelemetry {
    cores: Vec<CpuCoreTelemetry>,
}

impl CpuTelemetry {
    pub fn new() -> Self {
        let core_count = num_cpus::get();
        let cores = (0..core_count)
        .map(|i| CpuCoreTelemetry {core_num: i, temp: 0.0})
        .collect();
    CpuTelemetry { cores }    
    }
}

#[cfg(target_os = "linux")]
impl CpuTelemetry {
    // Refresh telemetry
    pub fn refresh(&mut self) {
        self.get_temperature();
    }
    // Get temperature telemetry
    fn get_temperature(&mut self) {
        for core in &mut self.cores {
            println!("I got the temps dawg")
        }
    }
}