use std::process::Command;
use crate::traits::telemetry::Telemetry;

#[derive(Debug)]
pub struct Storage {
    //static
    pub max_storage: u64,
    //dynamic
    pub available_storage: u64,
}

impl Storage {
    pub fn new() -> Self {
        let mut storage = Storage {
            max_storage: 0,
            available_storage: 0,
        };
        storage.set_max_storage();
        storage
    }
    fn set_max_storage(&mut self) {
        let lines = self.parse_terminal_output("df -h", "dev/nvme1n1p2");
        let value = self.filter_alphas(&lines[1]); 
        self.max_storage = value.trim().parse::<u64>().expect("Could not parse the string");
        
    }
    fn get_available_storage(&mut self) {
        let lines = self.parse_terminal_output("df -h", "dev/nvme1n1p2");
        let value = self.filter_alphas(&lines[3]); 
        self.available_storage = value.parse::<u64>().unwrap();

    }
    //helpers
    fn parse_terminal_output(&self, command: &str, str_match: &str) -> Vec<String> {
        let output = Command::new("sh")
            .arg("-c")
            .arg(command)
            .output()
            .expect("Failed to execute command");

        let stdout = String::from_utf8(output.stdout)
            .expect("Failed to convert output to UTF-8");

        let filtered_line = stdout.lines()
            .find(|line| line.contains(str_match))
            .unwrap_or("");

        filtered_line.trim().split_whitespace().map(|s| s.to_string()).collect()
    }
    fn filter_alphas(&self, input: &str) -> String {
        input.chars().filter(|c| c.is_ascii_digit()).collect()
    }
}

impl Telemetry for Storage {
    fn refresh(&mut self) {
        self.get_available_storage()
        
    }
}