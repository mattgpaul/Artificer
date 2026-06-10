use super::bar::{Bar, TimeAggregation};
use time::OffsetDateTime;

pub trait Historical {
    type Error;

    async fn get_ohlcv(
        &self,
        ticker: &str,
        aggregation: TimeAggregation,
        from: OffsetDateTime,
        to: OffsetDateTime,
    ) -> Result<Vec<Bar>, Self::Error>;
}
