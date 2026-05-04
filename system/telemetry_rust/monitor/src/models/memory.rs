use std::fs;
use crate::traits::telemetry::Telemetry;

#[derive(Debug)]
pub struct Memory {
    // static
    pub max_memory: f64,
    // dynamic
    pub free_memory: f64,
}

impl Memory {
    pub fn new() -> Option<Self> {
        let mut memory = Memory {
            max_memory: 0.0,
            free_memory: 0.0,
        };
        // set static variables
        memory.set_max_memory();
        // get dynamic variables
        memory.get_free_memory();
        Some(memory)
    }
    // set max memory
    fn set_max_memory(&mut self) {
        if let Some(max_memory) = parse_memory_value("MemTotal") {
            self.max_memory = max_memory / 1000000.0;
        }
    }
    // get allocated memory
    fn get_free_memory(&mut self) {
        if let Some(free_memory) = parse_memory_value("MemAvailable") {
            self.free_memory = free_memory / 1000000.0;
        }
    }
}

impl Telemetry for Memory {
    fn refresh(&mut self) {
        self.get_free_memory();
    }
}

/*Helper Functions */
// read meminfo line and extract integer value
fn parse_memory_value(value: &str) -> Option<f64> {
    let meminfo_path = "/proc/meminfo";
    let contents = fs::read_to_string(meminfo_path).ok()?;
    for line in contents.lines() {
        if line.contains(value) {
            return line.split_whitespace()
                .nth(1)
                .and_then(|s| s.parse::<f64>().ok())
        }
    }
    None
}