use super::bar::{Bar, TimeAggregation};
use time::UtcDateTime;

pub trait Historical {
    type Error;

    async fn get_ohlcv(
        &self,
        ticker: &str,
        aggregation: TimeAggregation,
        from: UtcDateTime,
        to: UtcDateTime,
    ) -> Result<Vec<Bar>, Self::Error>;
}
