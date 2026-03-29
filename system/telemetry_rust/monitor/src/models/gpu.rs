use std::fs;

struct Gpu {
    vendor_name: String,
    model_name: String,
    max_clock_speed: u64,
    edge_temp_c: f64,
    junction_temp_c: f64,
    memory_temp_c: f64,
    fan_speed_rpm: u64,
    max_fan_speed_rpm: u64,
    usage: u64,
    fps: u64,
    volts: u64,
}

impl Gpu {
    fn new() -> Self {
        Gpu {
            vendor_name: "N/A".to_string(),
            model_name: "N/A".to_string(),
            max_clock_speed: 0,
            edge_temp_c: 0.0,
            junction_temp_c: 0.0,
            memory_temp_c: 0.0,
            fan_speed_rpm: 0,
            max_fan_speed_rpm: 0,
            usage: 0,
            fps: 0,
            volts: 0,
        }
    }
}