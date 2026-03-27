
pub trait Telemetry {
    // refresh telemetry entries
    fn refresh(&mut self);
}

pub trait Thermal {
    fn get_temperature(&mut self);
}