use super::UnixMs;

pub enum TimeAggregation {
    Minute(u32),
    Hour(u32),
    Day,
    Week,
    Month,
    Quarter,
    Year,
}

#[derive(Debug, Copy, Clone)]
pub struct Bar {
    pub ticker: [u8; 8],
    pub timestamp: UnixMs,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: u64,
}

pub const fn to_ticker(s: &[u8]) -> [u8; 8] {
    let mut buf = [0u8; 8];
    let mut i = 0;
    while i < s.len() && i < 8 {
        buf[i] = s[i];
        i += 1;
    }
    buf
}

