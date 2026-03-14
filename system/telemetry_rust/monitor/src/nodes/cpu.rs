
struct CpuCoreTelemetry {
    core_num: u8,
    temp: f64,
}

impl CpuCoreTelemetry {
    // Constructor to set initial values
    fn new(core_num: u8, temp: f64) -> Self {
        CpuCoreTelemetry { core_num, temp }
    }

    // Core getter
    fn get_core_num(&self) -> u8 {
        self.core_num
    }

    // Temp setter
    fn set_core_temp(&mut self, temp: f64) {
        self.temp = temp;
    }

    // Temp getter
    fn get_core_temp(&self) -> f64 {
        self.temp
    }

}
pub struct CpuTelemetry {
    manufacturer: String,
    model: String,
    num_cores: u8,
    core_telemetry: Vec<CpuCoreTelemetry>,
}

