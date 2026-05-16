use std::path::PathBuf;
use std::time::SystemTime;
use crate::traits::utils::read_value_from_file;
use crate::traits::telemetry::Telemetry;

#[derive(Debug, Clone, PartialEq)]
pub struct Network {
    sys_path: PathBuf,
    time: SystemTime,
    //static 
    pub max_port_speed: u64,
    //dynamic
    pub downlink_bytes: u64,
    pub downlink_bps: f64,
    pub uplink_bytes: u64,
    pub uplink_bps: f64,
}

impl Network {
    pub fn new() -> Option<Self> {
        let mut network = Network {
            sys_path: PathBuf::from("/sys/class/net/eno1/"),
            time: SystemTime::now(),
            max_port_speed: 0,
            downlink_bytes: 0,
            downlink_bps: 0.0,
            uplink_bytes: 0,
            uplink_bps: 0.0,
        };
        network.set_max_port_speed();
        network.get_downlink_bytes();
        network.get_uplink_bytes();
        Some(network)
    }
    fn set_max_port_speed(&mut self) {
        if let Some(value) = read_value_from_file(&self.sys_path.join("speed")) {
            self.max_port_speed = value
        }
        
    }
    // get downlink bytes and add to the previous
    fn get_downlink_bytes(&mut self) {
        if let Some(value) = read_value_from_file(&self.sys_path.join("statistics/rx_bytes")) {
            self.downlink_bytes = value;
        }
    }
    // get uplink bytes and add to the previous
    fn get_uplink_bytes(&mut self) {
        if let Some(value) = read_value_from_file(&self.sys_path.join("statistics/tx_bytes")) {
            self.uplink_bytes = value;
        }
    }
}


impl Telemetry for Network {
    fn refresh(&mut self) {
        // store t0 data first
        let t0_time = self.time;
        let t0_downlink = self.downlink_bytes;
        let t0_uplink = self.uplink_bytes;
        // then refresh
       self.get_downlink_bytes();
       self.get_uplink_bytes(); 
       self.time = SystemTime::now();
       // calculate deltas
       let downlink_delta = self.downlink_bytes.saturating_sub(t0_downlink);
       let uplink_delta = self.uplink_bytes.saturating_sub(t0_uplink);
       if let Ok(dt) = self.time.duration_since(t0_time) {
            self.downlink_bps = downlink_delta as f64 / dt.as_secs_f64();
            self.uplink_bps = uplink_delta as f64 / dt.as_secs_f64();
       }
    }
}

