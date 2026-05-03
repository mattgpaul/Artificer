use std::thread;
use std::time::Duration;

mod models;
mod service;
mod traits;

use service::Service;
// ticks in ms
const TICK: u64 = 1000;
fn main() {
    let mut monitor = Service::new();
    // Main loop
    loop {
        monitor.tick();
        //sleep
        thread::sleep(Duration::from_millis(TICK));
    }
}

