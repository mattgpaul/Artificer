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
    output.append(f"{'=' * 80}")

    buy_count = (signals["signal_type"] == "buy").sum()
    sell_count = (signals["signal_type"] == "sell").sum()

    output.append(f"Summary: {buy_count} BUY signals, {sell_count} SELL signals")
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
    output.append(f"Win Rate:          {metrics.get('win_rate', 0.0):.2f}%")
    output.append(f"Avg Return %:      {metrics.get('avg_return_pct', 0.0):.2f}%")

    # Format avg_time_held
    avg_time_held_hours = metrics.get('avg_time_held', 0.0)
    if avg_time_held_hours < 24:
        time_held_str = f"{avg_time_held_hours:.1f} hours"
    else:
        days = int(avg_time_held_hours // 24)
        hours = int(avg_time_held_hours % 24)
        time_held_str = f"{days} days {hours} hours"

    output.append(f"Avg Time Held:     {time_held_str}")
    output.append(f"Avg Efficiency:    {metrics.get('avg_efficiency', 0.0):.1f}%")

    output.append(f"\n{'=' * 80}\n")

    return "\n".join(output)


def format_trade_details(trades):
    if trades.empty:
        return "No completed trades to display"

    output = []
    output.append(f"\n{'=' * 120}")
    output.append("Detailed Trade History")
    output.append(f"{'=' * 120}\n")

    # Header with all columns matching user's requirement
    output.append(
        f"{'STATUS':<8} {'ENTRY DATE':<11} {'ENTRY TIME':<9} {'EXIT DATE':<11} {'EXIT TIME':<9} "
        f"{'SYMBOL':<8} {'ENTRY':<10} {'EXIT':<10} {'SIZE':<10} {'SIDE':<6} "
        f"{'RETURN $':<12} {'RETURN %':<10} {'STRATEGY':<20} {'EFFICIENCY':<10}"
    )
    output.append("-" * 120)

    # Rows
    for _, trade in trades.iterrows():
        entry_date = trade["entry_time"].strftime("%Y-%m-%d")
        entry_time = trade["entry_time"].strftime("%H:%M:%S")
        exit_date = trade["exit_time"].strftime("%Y-%m-%d")
        exit_time = trade["exit_time"].strftime("%H:%M:%S")

        status = trade.get("status", "CLOSED")
        symbol = trade.get("ticker", "")
        entry_price = trade["entry_price"]
        exit_price = trade["exit_price"]
        size = trade["shares"]
        side = trade.get("side", "LONG")
        return_dollar = trade["gross_pnl"]
        return_pct = trade["gross_pnl_pct"]
        strategy = trade.get("strategy", "")
        efficiency = trade.get("efficiency", 0.0)

        output.append(
            f"{status:<8} {entry_date:<11} {entry_time:<9} {exit_date:<11} {exit_time:<9} "
            f"{symbol:<8} {entry_price:<10.2f} {exit_price:<10.2f} {size:<10.2f} {side:<6} "
            f"{return_dollar:<12.2f} {return_pct:<10.2f}% {strategy:<20} {efficiency:<10.1f}%"
        )

    output.append(f"\n{'=' * 120}\n")

    return "\n".join(output)
