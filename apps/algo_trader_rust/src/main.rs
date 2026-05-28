mod data;

use data::bar::{Bar, to_ticker};
use data::UnixMs;

fn main() {
    env_logger::init();

    log::info!("starting up");
    log::debug!("interesting value");
    log::warn!("heads up");
    log::error!("oh no!");

    let bar = Bar{
        ticker: to_ticker(b"AAPL"),
        timestamp: UnixMs(179000000),
        open: 10.0,
        high: 11.0,
        low: 8.0,
        close: 9.0, 
        volume: 100000000,
    };

    println!("{bar:?}");

}
