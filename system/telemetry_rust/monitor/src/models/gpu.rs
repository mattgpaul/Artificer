use std::{fs, io::Read};
use crate::{models::gpu, traits::pci_map::gpu_pci_maps};

#[derive(Debug)]
pub struct Gpu {
    vendor_name: String,
    device_name: String,
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
    pub fn new() -> Self {
        let mut gpu = Gpu {
                        vendor_name: "N/A".to_string(),
                        device_name: "N/A".to_string(),
                        max_clock_speed: 0,
                        edge_temp_c: 0.0,
                        junction_temp_c: 0.0,
                        memory_temp_c: 0.0,
                        fan_speed_rpm: 0,
                        max_fan_speed_rpm: 0,
                        usage: 0,
                        fps: 0,
                        volts: 0,
        };
        gpu.set_vendor_and_device();
        gpu
    }
    // set gpu vendor and device names
    fn set_vendor_and_device(&mut self) {
        // get vendor and device codes
        let (vendor_id, device_id) = get_vendor_and_device_codes();
        // set vendor name from id
        self.vendor_name = gpu_pci_maps::get_gpu_vendor(&vendor_id);
        self.device_name = gpu_pci_maps::get_gpu_device(&vendor_id, &device_id);
    }
}
// helper to get modalias contents
fn get_modalias() -> Option<String> {
    // get modalias contents
    // assume for now that the one we want is in the lowest integer card in the directory
    const DEVICE_PATH: &str = "/sys/class/drm";
    let card_path = fs::read_dir(DEVICE_PATH).ok()?;
    // loop directories until we find /device/modalias
    //TODO: this logic is not great
    for dir_entry in card_path {
        let Ok(dir_entry) = dir_entry else { continue };
        let path = dir_entry.path();
        // read the contents of modalias
        let Ok(mut f) = fs::File::open(path.join("device/modalias")) else { continue };
        let mut contents = String::new();
        f.read_to_string(&mut contents).ok()?;
        return Some(contents);
    }
    None
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