pub mod gpu_pci_maps {
    pub fn get_gpu_vendor(hex_id: u16) -> Option<&'static str> {
        match hex_id {
            0x10DE => Some("NVIDIA"),
            0x1002 => Some("AMD"),
            0x8086 => Some("Intel"),
            _ => None,
        }
    }
    pub fn get_gpu_device(vendor_hex_id: u16, model_hex_id: u16) -> Option<&'static str> {
        if let Some(vendor) = get_gpu_vendor(vendor_hex_id) {
            match vendor {
                "NVIDIA" => {
                    match model_hex_id {
                        0x2C02 => Some("GeForce RTX 5080"),
                        _ => None,
                    } 
                },
                "AMD" => {
                    match model_hex_id {
                        0x744C => Some("Radeon RX 7900 XTX"),
                        _ => None,
                    }
                },
                "Intel" => {
                    match model_hex_id {
                        0xE20B => Some("Arc B580"),
                        _ => None,
                    }
                },
                _ => None,
            }
        } else {
            None
        }
    }
} 
