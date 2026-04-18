use std::{fs, io::Read};
use std::path::PathBuf;
use crate::traits::telemetry::Telemetry;
use crate::traits::pci_map::gpu_pci_maps;

#[derive(Debug)]
pub struct Gpu {
    // static
    sys_path: PathBuf,
    hwmon_path: PathBuf,
    pub vendor_name: String,
    pub device_name: String,
    pub max_clock_speed: u64,
    pub max_fan_speed_rpm: u64,
    pub max_vram: u64,
    pub critical_edge_temp_c: u64,
    pub critical_junction_temp_c: u64,
    pub critical_memory_temp_c: u64,
    pub emergency_edge_temp_c: u64,
    pub emergency_junction_temp_c: u64,
    pub emergency_memory_temp_c: u64,
    pub max_power: u64,
    // dynamic
    pub edge_temp_c: f64,
    pub junction_temp_c: f64,
    pub memory_temp_c: f64,
    pub fan_speed_rpm: u64,
    pub usage: u64,
    pub vram_usage: u64,
    pub power: u64,
    pub thermal_throttle: bool,
    pub fps: u64,
}

impl Gpu {
    pub fn new() -> Self {
        let mut gpu = Gpu {
                        // static
                        sys_path: PathBuf::from("/sys/class/drm/"),
                        hwmon_path: PathBuf::from("/sys/class/drm/"),
                        vendor_name: "N/A".to_string(),
                        device_name: "N/A".to_string(),
                        max_clock_speed: 0,
                        max_fan_speed_rpm: 0,
                        max_vram: 0,
                        critical_edge_temp_c: 0,
                        critical_junction_temp_c: 0,
                        critical_memory_temp_c: 0,
                        emergency_edge_temp_c: 0,
                        emergency_junction_temp_c: 0,
                        emergency_memory_temp_c: 0,
                        max_power: 0,
                        //dynamic
                        edge_temp_c: 0.0,
                        junction_temp_c: 0.0,
                        memory_temp_c: 0.0,
                        fan_speed_rpm: 0,
                        usage: 0,
                        vram_usage: 0,
                        power: 0,
                        thermal_throttle: false,
                        fps: 0,
        };
        // set static variables during initialization
        gpu.set_device_paths();
        gpu.set_vendor_and_device();
        gpu.set_max_clock();
        gpu.set_max_fan_speed();
        gpu.set_max_vram();
        gpu.set_static_temps();
        gpu.set_max_power();
        gpu
    }
    // set the primary path to read device telemetry from
    // set the primary path to read device telemetry from
    fn set_device_paths(&mut self) {
        /*
        gets the primary device paths for the gpu
        as used on a linux system for AMD
        sets the paths for "sys_path" and "hwmon_path"
         */
        let card_path = get_card_num_path();
        let hwmon_path = get_hwmon_path();

        self.sys_path = card_path.clone();
        self.hwmon_path = hwmon_path;
    }
    // set gpu vendor and device names
    fn set_vendor_and_device(&mut self) {
        // get vendor and device codes
        let (vendor_id, device_id) = get_vendor_and_device_codes();
        // set vendor name from id
        self.vendor_name = gpu_pci_maps::get_gpu_vendor(&vendor_id);
        self.device_name = gpu_pci_maps::get_gpu_device(&vendor_id, &device_id);
    }
    // get gpu max clock speed
    fn set_max_clock(&mut self) {
        // get the max gpu clock speed in MHz and set it to self.max_clock_speed
        //TODO: Need to figure out how to best parse this from the system
    }
    // set max fan speed RPM
    fn set_max_fan_speed(&mut self) {
        /*
        find and set the max fan speed of the gpu fan
        may not be present, so should not panic on a failure to find
         */
        if let Some(value) = read_value_from_file(&self.hwmon_path.join("fan1_max")) {
            self.max_fan_speed_rpm = value;
        }
    }
    // set max vram
    fn set_max_vram(&mut self) {
        /*
        set max vram using the device path
         */
        if let Some(value) = read_value_from_file(&self.sys_path.join("mem_info_vram_total")) {
            self.max_vram = value / 1024 / 1024; // Convert from bytes to MB
        }
    }
    // get all critical and emergency gpu temps
    fn set_static_temps(&mut self) {
        /*
        get all critical and emergency gpu temps and set them in the struct
         */
        // Read critical temperatures
        if let Some(value) = read_value_from_file(&self.hwmon_path.join("temp1_crit")) {
            self.critical_edge_temp_c = value / 1000; // Convert from millidegrees to degrees
        }

        if let Some(value) = read_value_from_file(&self.hwmon_path.join("temp2_crit")) {
            self.critical_junction_temp_c = value / 1000;
        }

        if let Some(value) = read_value_from_file(&self.hwmon_path.join("temp3_crit")) {
            self.critical_memory_temp_c = value / 1000;
        }

        // Read emergency temperatures
        if let Some(value) = read_value_from_file(&self.hwmon_path.join("temp1_emergency")) {
            self.emergency_edge_temp_c = value / 1000;
        }

        if let Some(value) = read_value_from_file(&self.hwmon_path.join("temp2_emergency")) {
            self.emergency_junction_temp_c = value / 1000;
        }

        if let Some(value) = read_value_from_file(&self.hwmon_path.join("temp3_emergency")) {
            self.emergency_memory_temp_c = value / 1000;
        }
    }
    // get max power
    fn set_max_power(&mut self) {
        // set maximum power of the gpu
        if let Some(value) = read_value_from_file(&self.hwmon_path.join("power1_cap_max")){
            self.max_power = value as u64 / 1000000;
        }
    }
    // get all gpu temps
    fn get_dynamic_temps(&mut self) {
        /*
        get the edge temp, junction temp, and memory temp in deg C
        and set them to their corresponding fields in the struct
         */
        // Read edge temperature
        if let Some(value) = read_value_from_file(&self.hwmon_path.join("temp1_input")) {
            self.edge_temp_c = value as f64 / 1000.0; // Convert from millidegrees to degrees
        }

        // Read junction temperature
        if let Some(value) = read_value_from_file(&self.hwmon_path.join("temp2_input")) {
            self.junction_temp_c = value as f64 / 1000.0;
        }

        // Read memory temperature
        if let Some(value) = read_value_from_file(&self.hwmon_path.join("temp3_input")) {
            self.memory_temp_c = value as f64 / 1000.0;
        }
    }
    // get fan speeds

    fn get_fan_speed(&mut self) {
        /*
        get the current and maximum fan speed RPM for the gpu
        not all systems contain this, so it should not panic
        if it cannot be found.
        values set to their corresponding fields in the struct
         */
        // Read current fan speed
        if let Some(value) = read_value_from_file(&self.hwmon_path.join("fan1_input")) {
            self.fan_speed_rpm = value;
        }
    }
    // get current gpu usage
    fn get_usage(&mut self) {
        /*
        get current gpu usage in %, and set it to the struct
         */
        if let Some(value) = read_value_from_file(&self.sys_path.join("gpu_busy_percent")) {
            self.usage = value as u64;
        }
    }
    // get current vram usage
    fn get_vram_usage(&mut self) {
        if let Some(value) = read_value_from_file(&self.sys_path.join("mem_info_vram_used")) {
            self.vram_usage = value / 1024 / 1024;
        }
    }
    // get frames per second
    fn get_fps(&mut self) {
        /*
        not sure how to implement this right now
        mark it TODO
         */
    }
    // get gpu volts
    fn get_power(&mut self) {
        /*
        get gpu power in Watts
         */
        if let Some(value) = read_value_from_file(&self.hwmon_path.join("power1_input")) {
            self.power = value as u64 / 1000000;
        }
    }

}
/* TRAIT IMPLEMENTATIONS */
impl Telemetry for Gpu {
    fn refresh(&mut self) {
        // refresh all dynamic values
        self.get_dynamic_temps();
        self.get_fan_speed();
        self.get_fps();
        self.get_power();
        self.get_usage();
        self.get_vram_usage();
    }
}
/* PRIVATE HELPER FUNCTIONS */
// helper to determine which card number to use
fn get_card_num_path() -> PathBuf {
    /*
    Looks in "/sys/class/drm/" to find what cards are available there
    and determines which card{n} is the card we want to use 
    Returns the full path "/sys/class/drm/card{n}/device/" 
    */
    const DEVICE_PATH: &str = "/sys/class/drm";

    // Read the directory entries
    let entries = match fs::read_dir(DEVICE_PATH) {
        Ok(entries) => entries,
        Err(_) => return PathBuf::from("/sys/class/drm/card0/device/"),
    };

    // Find the first standard card directory that has a device directory
    // Standard cards are named card0, card1, etc. (not card2-DP-4)
    for entry in entries {
        if let Ok(entry) = entry {
            let path = entry.path();
            if let Some(name) = path.file_name() {
                let name_str = name.to_string_lossy();
                // Only consider standard card names (no dashes)
                if name_str.starts_with("card") && !name_str.contains('-') {
                // Check if this card has a device directory
                let device_path = path.join("device");
                if device_path.exists() {
                    return device_path;
                }
            }
        }
    }
    }

    // Fallback to card0 if no valid card found
    PathBuf::from("/sys/class/drm/card0/device/")
}

fn get_hwmon_path() -> PathBuf {
    let card_path = get_card_num_path();
    
    fs::read_dir(&card_path)
        .unwrap()
        .flatten()
        .filter_map(|entry| {
            let path = entry.path();
            let name = path.file_name()?.to_str()?;
            if name.starts_with("hwmon") {
                // Check if this hwmon directory contains another hwmon subdirectory
                if let Ok(sub_entries) = fs::read_dir(&path) {
                    for sub_entry in sub_entries.flatten() {
                        if let Some(sub_name) = sub_entry.path().file_name().and_then(|n| n.to_str()) {
                            if sub_name.starts_with("hwmon") {
                                return Some(sub_entry.path());
                            }
                        }
                    }
                }
                Some(path)
            } else {
                None
            }
        })
        .next()
        .expect("Failed to find hwmon path in device directory")
}

// helper to get modalias contents
fn get_modalias() -> Option<String> {
    // get modalias contents
    // use the existing helper to get the card path
    let card_path = get_card_num_path();
    let modalias_path = card_path.join("modalias");
        // read the contents of modalias
        let mut contents = String::new();
    let result = fs::File::open(&modalias_path)
        .and_then(|mut f| f.read_to_string(&mut contents))
        .ok();

    if result.is_some() {
        Some(contents)
    } else {
    None
}
}
// helper to return the vendor and device of the gpu
fn get_vendor_and_device_codes() -> (u16, u16) {
    // get modalias
    let modalias = get_modalias().expect("Failed to get modalias");
    let mut vendor_id: u16 = 0;
    let mut device_id: u16 = 0;

    // Split on ':' to get the main parts
    let parts: Vec<&str> = modalias.split(':').collect();
      // The second part contains the vendor and device information
    let second_part = parts[1];

    // Extract vendor ID (starts with 'v' followed by 4 hex digits)
    if let Some(vendor_start) = second_part.find('v') {
        let vendor_hex = &second_part[vendor_start + 1.. vendor_start + 9];
        vendor_id = u16::from_str_radix(&vendor_hex, 16).expect("Failed to parse vendor ID");
    }

    // Extract device ID (starts with 'd' followed by 4 hex digits)
    if let Some(device_start) = second_part.find('d') {
        let device_hex = &second_part[device_start + 1.. device_start + 9];
        device_id = u16::from_str_radix(&device_hex, 16).expect("Failed to parse device ID");
    }
    (vendor_id, device_id)
}
// Helper function to read and parse numeric values from files
fn read_value_from_file(path: &PathBuf) -> Option<u64> {
    if let Ok(contents) = fs::read_to_string(path) {
        if let Ok(value) = contents.trim().parse::<u64>() {
            return Some(value);
        }
    }
    None
}