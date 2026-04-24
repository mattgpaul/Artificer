use std::path::PathBuf;
use crate::traits::telemetry::Telemetry;
use crate::traits::utils::read_value_from_file;

#[derive(Debug)]
pub struct Memory {
    // static
    pub max_memory: u64,
    // dynamic
    pub free_memory: u64,
}

impl Memory {
    pub fn new() -> Self {
        let mut memory = Memory {
            max_memory: 0,
            free_memory: 0,
        };
        // set static variables
        memory.set_max_memory();
        // get dynamic variables
        memory.get_free_memory();
        memory
    }
    // set max memory
    fn set_max_memory(&mut self) {
        todo!("this wont work. need to parse the variables after read");
        if let Some(value) = read_value_from_file(&PathBuf::from("/proc/meminfo")) {
            self.max_memory = value / 1000000; // convert to GB
        }
    }
    // get allocated memory
    fn get_free_memory(&mut self) {
        todo!("implement this using max memory approach");
    }

impl Telemetry for Memory {
    fn refresh(&mut self) {
        self.get_free_memory();
    }
}