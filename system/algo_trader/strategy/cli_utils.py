from system.algo_trader.datasource.sec.tickers import Tickers


def resolve_tickers(tickers_arg, logger):
    if tickers_arg == ["full-registry"]:
        logger.info("full-registry specified, fetching all tickers from SEC datasource...")
        ticker_source = Tickers()
        all_tickers_data = ticker_source.get_tickers()

        if all_tickers_data is None:
            logger.error("Failed to retrieve tickers from SEC")
            raise ValueError("Failed to retrieve tickers from SEC datasource")

        ticker_list = []
        for _key, value in all_tickers_data.items():
            if isinstance(value, dict) and "ticker" in value:
                ticker_list.append(value["ticker"])

        logger.info(f"Retrieved {len(ticker_list)} tickers from SEC datasource")
        return ticker_list
    else:
        logger.info(f"Processing {len(tickers_arg)} specific tickers: {tickers_arg}")
        return tickers_arg


def format_signal_summary(signals):
    if signals.empty:
        return "No signals generated"

    output = []
    output.append(f"\n{'=' * 80}")
    output.append(f"Generated {len(signals)} trading signals")
    output.append(f"{'=' * 80}\n")

    for _, row in signals.iterrows():
        signal_time = row["signal_time"].strftime("%Y-%m-%d %H:%M:%S")
        signal_type = row["signal_type"].upper()
        price = row["price"]
        confidence = row.get("confidence", 0.0)
        ticker = row.get("ticker", "N/A")

        output.append(
            f"[{signal_time}] {ticker} - {signal_type:4s} @ ${price:.2f} "
            f"(confidence: {confidence:.2%})"
        )

    output.append(f"\n{'=' * 80}")

    buy_count = (signals["signal_type"] == "buy").sum()
    sell_count = (signals["signal_type"] == "sell").sum()
    avg_confidence = signals.get("confidence", 0.0).mean()

    output.append(f"Summary: {buy_count} BUY signals, {sell_count} SELL signals")
    output.append(f"Average confidence: {avg_confidence:.2%}")
    output.append(f"{'=' * 80}\n")

    return "\n".join(output)
