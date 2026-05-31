use time::UtcDateTime;

pub enum Minutes {
    One,
    Two,
    Five,
    Fifteen,
    Thirty,
    Ninety,
}

impl Minutes {
    pub fn as_string(self) -> &'static str {
        match self {
            Minutes::One => "1m",
            Minutes::Two => "2m",
            Minutes::Five => "5m",
            Minutes::Fifteen => "15m",
            Minutes::Thirty => "30m",
            Minutes::Ninety => "90m",
        }
    }
}

pub enum TimeAggregation {
    Minute(Minutes),
    Hour,
    Day,
    Week,
    Month,
    Quarter,
    Year,
}

impl TimeAggregation {
    pub fn as_string(self) -> &'static str {
        match self {
            TimeAggregation::Minute(m) => m.as_string(),
            TimeAggregation::Hour => "1h",
            TimeAggregation::Day => "1d",
            TimeAggregation::Week => "1w",
            TimeAggregation::Month => "1mo",
            TimeAggregation::Quarter => "1q",
            TimeAggregation::Year => "1y",
        }
    }
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

