pub mod pci_maps {
    use std::collections::HashMap;
    pub fn get_gpu_vendor(hex_id: &u32) -> String {
        // init the hasmap
        let mut vendors = HashMap::new();
        // populate with the hex codes from gpu vendors
        vendors.insert(0x10DE, "NVIDIA");
        vendors.insert(0x1002, "AMD");
        vendors.insert(0x8086, "Intel");
        // return the appropriate string for the hex code
        vendors.get(hex_id)
            .expect("Unknown hex ID for the vendor")
            .to_string()
    }
    pub fn get_gpu_model(vendor_hex_id: &u32, model_hex_id: &u32) -> String {
        // init the hashmap
        let mut models = HashMap::new();
        // match case on the vendor hex code
        // then populate the hashmap for model codes
        // match on model code and return the string
        let vendor = get_gpu_vendor(vendor_hex_id);

        match vendor.as_str() {
            // NVIDIA case
            "NVIDIA" => {
                models.insert(0x2C02, "GeForce RTX 5080");
            },
            // AMD case
            "AMD" => {
                models.insert(0x744C, "Radeon RX 7900 XTX");
            },
            "Intel" => {
                models.insert(0xE20B, "Arc B580");
            },
            _ => panic!("Unknon GPU for vendor code: {}", vendor_hex_id),
            //return the correct name for the model
        }
        models.get(model_hex_id)
            .expect("Could not find model for given vendor and model hex codes")
            .to_string()
    }
} 
