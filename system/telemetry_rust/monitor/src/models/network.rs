use std::path::PathBuf;

use crate::traits::utils::read_value_from_file;
use crate::traits::telemetry::Telemetry;

#[derive(Debug)]
pub struct Network {
    sys_path: PathBuf,
    //static 
    pub max_port_speed: u64,
    //dynamic
    pub downlink_bytes: u64,
    pub uplink_bytes: u64,
}

impl Network {
    pub fn new() -> Self {
        let mut network = Network {
            sys_path: PathBuf::from("/sys/class/net/eno1/"),
            max_port_speed: 0,
            downlink_bytes: 0,
            uplink_bytes: 0,
        };
        network.set_max_port_speed();
        network.get_downlink_bytes();
        network.get_uplink_bytes();
        network
    }
    fn set_max_port_speed(&mut self) {
        if let Some(value) = read_value_from_file(&self.sys_path.join("speed")) {
            self.max_port_speed = value
        }
        
    }
    // get downlink bytes and add to the previous
    fn get_downlink_bytes(&mut self) {
        if let Some(value) = read_value_from_file(&self.sys_path.join("statistics/rx_bytes")) {
            self.downlink_bytes += value
        }
    }
    // get uplink bytes and add to the previous
    fn get_uplink_bytes(&mut self) {
        if let Some(value) = read_value_from_file(&self.sys_path.join("statistics/tx_bytes")) {
            self.uplink_bytes += value
        }
    }
}


impl Telemetry for Network {
    fn refresh(&mut self) {
       self.get_downlink_bytes();
       self.get_uplink_bytes(); 
    }
}

