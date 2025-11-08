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


def format_journal_summary(metrics, ticker, strategy):
    output = []
    output.append(f"\n{'=' * 80}")
    output.append(f"Trading Journal Summary: {ticker} - {strategy}")
    output.append(f"{'=' * 80}\n")

    output.append(f"Total Trades:      {metrics['total_trades']}")
    output.append(f"Total Profit:      ${metrics['total_profit']:.2f}")
    output.append(f"Total Profit %:    {metrics['total_profit_pct']:.2f}%")
    output.append(f"Max Drawdown:      {metrics['max_drawdown']:.2f}%")
    output.append(f"Sharpe Ratio:      {metrics['sharpe_ratio']:.2f}")

    output.append(f"\n{'=' * 80}\n")

    return "\n".join(output)


def format_trade_details(trades):
    if trades.empty:
        return "No completed trades to display"

    output = []
    output.append(f"\n{'=' * 80}")
    output.append("Detailed Trade History")
    output.append(f"{'=' * 80}\n")

    # Header
    output.append(
        f"{'Entry Time':<20} {'Exit Time':<20} {'Entry $':<10} {'Exit $':<10} "
        f"{'P&L $':<12} {'P&L %':<10}"
    )
    output.append("-" * 80)

    # Rows
    for _, trade in trades.iterrows():
        entry_time = trade["entry_time"].strftime("%Y-%m-%d %H:%M:%S")
        exit_time = trade["exit_time"].strftime("%Y-%m-%d %H:%M:%S")
        entry_price = trade["entry_price"]
        exit_price = trade["exit_price"]
        gross_pnl = trade["gross_pnl"]
        gross_pnl_pct = trade["gross_pnl_pct"]

        output.append(
            f"{entry_time:<20} {exit_time:<20} {entry_price:<10.2f} {exit_price:<10.2f} "
            f"{gross_pnl:<12.2f} {gross_pnl_pct:<10.2f}%"
        )

    output.append(f"\n{'=' * 80}\n")

    return "\n".join(output)
