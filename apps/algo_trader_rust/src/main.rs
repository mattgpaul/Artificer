mod data;
mod scanner;

use time::macros::datetime;
use data::providers::yfinance;
use data::bar::TimeAggregation;
use data::provider::Historical;

#[tokio::main]
async fn main() {
    let provider = yfinance::Yfinance::new();
    let start = datetime!(2020-1-1 0:00:00.00 UTC);
    let end = datetime!(2020-1-31 23:59:59.99 UTC);
    let resp = provider.get_ohlcv("AAPL", TimeAggregation::Day, start, end).await.unwrap();
    println!("{resp:#?}");
}
