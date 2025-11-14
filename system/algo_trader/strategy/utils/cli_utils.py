"""CLI utility functions for strategy execution.

This module provides utility functions for ticker resolution, signal formatting,
and journal formatting used by the strategy execution CLI.
"""

import pandas as pd

from system.algo_trader.datasource.sec.tickers.main import Tickers


def get_sp500_tickers() -> list[str]:
    """Get list of S&P 500 ticker symbols.

    Fetches the current S&P 500 constituents from Wikipedia.

    Returns:
        List of S&P 500 ticker symbols. Returns empty list if fetch fails.

    Example:
        >>> tickers = get_sp500_tickers()
        >>> assert 'AAPL' in tickers
        >>> assert len(tickers) > 400
    """
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        # The first table contains the S&P 500 constituents
        sp500_df = tables[0]
        tickers = sp500_df["Symbol"].tolist()
        # Clean up ticker symbols (remove dots, convert to uppercase)
        tickers = [ticker.replace(".", "-") for ticker in tickers]
        return tickers
    except Exception:
        # Fallback to a static list if Wikipedia fetch fails
        # This is a snapshot of top S&P 500 tickers as of 2024
        # Note: This is a partial list. The full list should be fetched from Wikipedia.
        # For production use, the Wikipedia fetch should work, but this provides
        # a fallback for offline scenarios.
        return [
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "NVDA",
            "META",
            "TSLA",
            "BRK-B",
            "UNH",
            "JNJ",
            "V",
            "XOM",
            "JPM",
            "WMT",
            "PG",
            "MA",
            "CVX",
            "HD",
            "ABBV",
            "MRK",
            "PEP",
            "COST",
            "AVGO",
            "ADBE",
            "CSCO",
            "TMO",
            "CRM",
            "ACN",
            "NFLX",
            "DHR",
            "DIS",
            "VZ",
            "CMCSA",
            "ABT",
            "LIN",
            "NKE",
            "PM",
            "TXN",
            "NEE",
            "HON",
            "QCOM",
            "RTX",
            "AMGN",
            "BMY",
            "DE",
            "AMAT",
            "LOW",
            "INTU",
            "GE",
            "BKNG",
            "TJX",
            "AXP",
            "SYK",
            "ADP",
            "GILD",
            "ISRG",
            "MDT",
            "C",
            "ADI",
            "CB",
            "REGN",
            "ZTS",
            "EQIX",
            "NOW",
            "ELV",
            "BSX",
            "SNPS",
            "CDNS",
            "WM",
            "KLAC",
            "ITW",
            "ETN",
            "SHW",
            "CME",
            "HCA",
            "MCO",
            "CTAS",
            "FTNT",
            "MCK",
            "AON",
            "NXPI",
            "DXCM",
            "ICE",
            "EW",
            "PSA",
            "VRSK",
            "IDXX",
            "FAST",
            "CPRT",
            "ODFL",
            "CTSH",
            "PAYX",
            "ROST",
            "ANSS",
            "CDW",
            "WDAY",
            "EXPD",
            "PCAR",
            "FERG",
            "NDAQ",
            "ALGN",
            "TTD",
            "VRSN",
            "EBAY",
        ]


def resolve_tickers(tickers_arg, logger):
    """Resolve ticker symbols from command-line arguments.

    Handles three cases:
    1. Specific tickers: Returns the provided list as-is
    2. 'full-registry': Fetches all tickers from SEC datasource
    3. 'SP500': Fetches all S&P 500 ticker symbols

    Args:
        tickers_arg: List of ticker symbols, ['full-registry'], or ['SP500'].
        logger: Logger instance for logging resolution progress.

    Returns:
        List of resolved ticker symbols. Empty list if full-registry or SP500
        returns no data.

    Raises:
        ValueError: If full-registry fails to retrieve data from SEC.

    Example:
        >>> tickers = resolve_tickers(['AAPL', 'MSFT'], logger)
        >>> assert tickers == ['AAPL', 'MSFT']
        >>> all_tickers = resolve_tickers(['full-registry'], logger)
        >>> sp500_tickers = resolve_tickers(['SP500'], logger)
    """
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
    elif tickers_arg == ["SP500"]:
        logger.info("SP500 specified, fetching S&P 500 tickers...")
        ticker_list = get_sp500_tickers()
        if not ticker_list:
            logger.error("Failed to retrieve S&P 500 tickers")
            raise ValueError("Failed to retrieve S&P 500 tickers")
        logger.info(f"Retrieved {len(ticker_list)} S&P 500 tickers")
        return ticker_list
    else:
        logger.info(f"Processing {len(tickers_arg)} specific tickers: {tickers_arg}")
        return tickers_arg


def format_signal_summary(signals):
    """Format trading signals into a human-readable summary string.

    Args:
        signals: DataFrame containing trading signals with 'signal_type' column.

    Returns:
        Formatted string with signal summary including total count and
        breakdown by buy/sell signals. Returns "No signals generated" if empty.

    Example:
        >>> summary = format_signal_summary(signals_df)
        >>> print(summary)
    """
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
    """Format trading journal metrics into a human-readable summary string.

    Args:
        metrics: Dictionary containing performance metrics:
            - total_trades: Number of completed trades
            - total_profit: Total profit/loss in dollars
            - total_profit_pct: Total profit/loss percentage
            - max_drawdown: Maximum drawdown percentage
            - win_rate: Win rate percentage (optional)
            - avg_return_pct: Average return percentage (optional)
            - avg_time_held: Average time held in hours (optional)
            - avg_efficiency: Average efficiency percentage (optional)
        ticker: Stock ticker symbol for the journal.
        strategy: Strategy name for the journal.

    Returns:
        Formatted string with journal summary including all metrics.

    Example:
        >>> metrics = {'total_trades': 10, 'total_profit': 500.0, ...}
        >>> summary = format_journal_summary(metrics, 'AAPL', 'sma-crossover')
    """
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
    avg_time_held_hours = metrics.get("avg_time_held", 0.0)
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


def format_group_summary(metrics, strategy):
    """Format aggregate trading journal metrics across multiple tickers.

    Args:
        metrics: Dictionary containing aggregate performance metrics
            (same structure as format_journal_summary).
        strategy: Strategy name for the group summary.

    Returns:
        Formatted string with group summary including aggregate metrics.

    Example:
        >>> group_metrics = {'total_trades': 50, 'total_profit': 2500.0, ...}
        >>> summary = format_group_summary(group_metrics, 'sma-crossover')
    """
    output = []
    output.append(f"\n{'#' * 80}")
    output.append(f"GROUP SUMMARY: ALL TICKERS - {strategy}")
    output.append(f"{'#' * 80}\n")

    output.append(f"Total Trades:      {metrics['total_trades']}")
    output.append(f"Total Profit:      ${metrics['total_profit']:.2f}")
    output.append(f"Total Profit %:    {metrics['total_profit_pct']:.2f}%")
    output.append(f"Max Drawdown:      {metrics['max_drawdown']:.2f}%")
    output.append(f"Win Rate:          {metrics.get('win_rate', 0.0):.2f}%")
    output.append(f"Avg Return %:      {metrics.get('avg_return_pct', 0.0):.2f}%")

    # Format avg_time_held
    avg_time_held_hours = metrics.get("avg_time_held", 0.0)
    if avg_time_held_hours < 24:
        time_held_str = f"{avg_time_held_hours:.1f} hours"
    else:
        days = int(avg_time_held_hours // 24)
        hours = int(avg_time_held_hours % 24)
        time_held_str = f"{days} days {hours} hours"

    output.append(f"Avg Time Held:     {time_held_str}")
    output.append(f"Avg Efficiency:    {metrics.get('avg_efficiency', 0.0):.1f}%")

    output.append(f"\n{'#' * 80}\n")

    return "\n".join(output)


def format_trade_details(trades):
    """Format detailed trade history into a human-readable table.

    Args:
        trades: DataFrame containing trade details with columns:
            - entry_time: Entry timestamp
            - exit_time: Exit timestamp
            - entry_price: Entry price
            - exit_price: Exit price
            - shares: Number of shares
            - gross_pnl: Gross profit/loss in dollars
            - gross_pnl_pct: Gross profit/loss percentage
            - ticker: Stock symbol (optional)
            - side: Trade side 'LONG' or 'SHORT' (optional)
            - strategy: Strategy name (optional)
            - status: Trade status (optional, default: 'CLOSED')
            - efficiency: Trade efficiency percentage (optional)

    Returns:
        Formatted string with detailed trade history table.
        Returns "No completed trades to display" if empty.

    Example:
        >>> details = format_trade_details(trades_df)
        >>> print(details)
    """
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
