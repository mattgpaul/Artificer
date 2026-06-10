use thiserror::Error;
use time::error::ComponentRange;
use yahoo_finance_api as yahoo;
use yahoo_finance_api::YahooError;
use time::{OffsetDateTime, UtcDateTime};

use crate::data::bar::{Bar, TimeAggregation};
use crate::data::provider::Historical;

#[derive(Debug)]
pub enum YfinanceError {
    Yahoo(YahooError),
    InvalidInterval(String),
    BadTimestamp(ComponentRange),
}

impl From<YahooError> for YfinanceError {
    fn from(e: YahooError) -> Self {
        YfinanceError::Yahoo(e)
    }
}

impl From<ComponentRange> for YfinanceError {
    fn from(e: ComponentRange) -> Self {
        YfinanceError::BadTimestamp(e)
    }
}

pub struct Yfinance {
    connector: yahoo::YahooConnector
}

impl Yfinance {
    pub fn new() -> Self {
        Yfinance {
            connector: yahoo::YahooConnector::new().unwrap()
        }
    }
}

impl Historical for Yfinance {
    type Error = YfinanceError;

    async fn get_ohlcv(
        &self,
        ticker: &str,
        aggregation: TimeAggregation,
        from: OffsetDateTime,
        to: OffsetDateTime,
    ) -> Result<Vec<Bar>, Self::Error> {
        check_interval(&aggregation, from)?;
        let response = self.connector.get_quote_history_interval(
            ticker,
            from,
            to,
            aggregation.as_string(),
        )
            .await?;
        let quotes = response.quotes()?;
        quotes
            .iter()
            .map(|q| -> Result<Bar, YfinanceError> {
                Ok(Bar {
                    ticker: ticker.to_string(),
                    timestamp: UtcDateTime::from_unix_timestamp(q.timestamp as i64)?,
                    open: q.open,
                    high: q.high,
                    low: q.low,
                    close: q.close,
                    volume: q.volume,
                })
            })
            .collect::<Result<Vec<Bar>, YfinanceError>>()
        }
    }

fn check_interval(
    interval: &TimeAggregation,
    date: OffsetDateTime,
) -> Result<(), YfinanceError> {
    match interval {
        TimeAggregation::Minute(_) | TimeAggregation::Hour => {
            // if an intraday interval is selected, date cannot be more
            // than 7 days into the past
            let now = OffsetDateTime::now_utc();
            let seven_days = time::Duration::days(7);
            if now - date > seven_days {
                return Err(YfinanceError::InvalidInterval(
                    "Date cannot be more than 7 days into the past for intraday intervals".to_string()
                ));
            }
            Ok(())
        },
        TimeAggregation::Day | TimeAggregation::Week | TimeAggregation::Month | TimeAggregation::Year | TimeAggregation::Quarter => {
            Ok(())
        }
    }
}
