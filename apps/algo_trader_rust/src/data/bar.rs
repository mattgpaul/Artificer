use time::UtcDateTime;

pub enum TimeAggregation {
    Minute(u32),
    Hour(u32),
    Day,
    Week,
    Month,
    Quarter,
    Year,
}

#[derive(Debug, Clone)]
pub struct Bar {
    pub ticker: String,
    pub timestamp: UtcDateTime,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: u64,
}

