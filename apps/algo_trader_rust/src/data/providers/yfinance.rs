use yahoo_finance_api as yahoo;
use yahoo_finance_api::YahooError;
use time::UtcDateTime;

use crate::data::bar::{Bar, TimeAggregation};
use crate::data::provider::Historical;

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
    type Error = YahooError;

    async fn get_ohlcv(
        &self,
        ticker: &str,
        aggregation: TimeAggregation,
        from: UtcDateTime,
        to: UtcDateTime,
    ) -> Result<Vec<Bar>, Self::Error> {
        let response = self.connector.get_quote_history(ticker, from.date(), to.date()).await?;
        
        let mut bars = Vec::new();
        for quote in response.quotes {
            if let (Some(open), Some(high), Some(low), Some(close), Some(volume), Some(timestamp)) = 
                (quote.open, quote.high, quote.low, quote.close, quote.volume, quote.timestamp) {
                
                let bar = Bar {
                    open,
                    high,
                    low,
                    close,
                    volume,
                    timestamp: timestamp.into(),
                };
                bars.push(bar);
            }
        }
        
        Ok(bars)
    } 
}
