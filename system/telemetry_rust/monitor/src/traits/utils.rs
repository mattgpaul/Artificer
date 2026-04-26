use std::fs;
use std::path::PathBuf;

// only works if there is only 1 value to read
pub fn read_value_from_file(path: &PathBuf) -> Option<u64> {
    if let Ok(contents) = fs::read_to_string(path) {
        if let Ok(value) = contents.trim().parse::<u64>() {
            return Some(value);
        }
    }
    None
}
