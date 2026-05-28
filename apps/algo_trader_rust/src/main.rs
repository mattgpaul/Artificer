mod data;
mod scanner;

use yahoo_finance_api as yahoo;
use time::macros::datetime;

#[tokio::main]
async fn main() {
    let provider = yahoo::YahooConnector::new().unwrap();
    let start = datetime!(2020-1-1 0:00:00.00 UTC);
    let end = datetime!(2020-1-31 23:59:59.99 UTC);
    let resp = provider.get_quote_history("AAPL", start, end).await.unwrap();
    let quotes = resp.quotes().unwrap();
    println!("{quotes:#?}");
}
