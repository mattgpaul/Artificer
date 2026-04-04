use std::{fs, io::Read};
use std::path::PathBuf;
use crate::{models::gpu, traits::pci_map::gpu_pci_maps};

#[derive(Debug)]
pub struct Gpu {
    // static
    sys_path: PathBuf,
    hwmon_path: PathBuf,
    edge_temp_path: PathBuf,
    junction_temp_path: PathBuf,
    memory_temp_path: PathBuf,
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
    // dynamic
    pub edge_temp_c: f64,
    pub junction_temp_c: f64,
    pub memory_temp_c: f64,
    pub fan_speed_rpm: u64,
    pub usage: u64,
    pub vram_usage: u64,
    pub volts: u64,
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
                        //dynamic
                        edge_temp_c: 0.0,
                        junction_temp_c: 0.0,
                        memory_temp_c: 0.0,
                        fan_speed_rpm: 0,
                        usage: 0,
                        vram_usage: 0,
                        volts: 0,
                        thermal_throttle: false,
                        fps: 0,
        };
        // set static variables during initialization
        gpu.set_device_paths();
        gpu.set_vendor_and_device();
        gpu
    }
    // set the primary path to read device telemetry from
    fn set_device_paths(&mut self) {
        /*
        gets the primary device paths for the gpu
        as used on a linux system for AMD
        sets the paths for "sys_path" and "hwmon_path"
         */
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
    fn get_max_clock(&mut self) {
        // get the max gpu clock speed in MHz and set it to self.max_clock_speed
        //TODO: Need to figure out how to best parse this from the system
    }
    // get all critical and emergency gpu temps
    fn get_static_temps(&mut self) {
        /*
        get all critical and emergency gpu temps and set them in the struct
         */
    }
    // get all gpu temps
    fn get_dynamic_temps(&mut self) {
        /*
        get the edge temp, junction temp, and memory temp in deg C
        and set them to their corresponding fields in the struct
         */
    }
    // get fan speeds
    fn get_fan_speed(&mut self) {
        /*
        get the current and maximum fan speed RPM for the gpu
        not all systems contain this, so it should not panic
        if it cannot be found.
        values set to their corresponding fields in the struct
         */
    }
    // get current gpu usage
    fn get_usage(&mut self) {
        /*
        get current gpu usage in %, and set it to the struct
         */
    }
    // get frames per second
    fn get_fps(&mut self) {
        /*
        not sure how to implement this right now
        mark it TODO
         */
    }
    // get gpu volts
    fn get_volts(&mut self) {
        /*
        get gpu voltage output in V
         */
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

    // Find the first card directory
    for entry in entries {
        if let Ok(entry) = entry {
            let path = entry.path();
            if path.file_name().map_or(false, |name| name.to_string_lossy().starts_with("card")) {
                // Check if this card has a device directory
                let device_path = path.join("device");
                if device_path.exists() {
                    return device_path;
                }
            }
        }
    }

    // Fallback to card0 if no valid card found
    PathBuf::from("/sys/class/drm/card0/device/")
}
// get hwmon path
fn get_hwmon_path() -> PathBuf {
    /*
    get the hwmon path from "get_card_num_path"
    path is appended to card num path with ".../hwmon/hwmon{n}/" */
    let card_path = get_card_num_path();
    // Remove the "/device" part to get the card directory
    let card_dir = card_path.parent().unwrap_or(&card_path);

    // Look for hwmon directories in the card directory
    let hwmon_entries = fs::read_dir(card_dir).ok();

    if let Some(entries) = hwmon_entries {
        for entry in entries {
            if let Ok(entry) = entry {
                let path = entry.path();
                if path.file_name().map_or(false, |name| name.to_string_lossy().starts_with("hwmon")) {
                    return path;
                }
            }
        }
    }

    // Fallback to a safe default if hwmon is not found
    PathBuf::from("/sys/class/drm/card0/device/hwmon/hwmon0/")
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