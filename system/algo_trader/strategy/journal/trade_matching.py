"""Trade matching for trading strategies.

This module provides functionality to match trading signals (buy/sell) into
executed trades, calculating PnL, efficiency, and other trade metrics.
"""

import math

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.journal.efficiency import calculate_efficiency


def _initialize_position_state(ticker: str, position_state: dict, trade_id_counters: dict) -> None:
    """Initialize position state for a ticker if it doesn't exist.

    Args:
        ticker: Ticker symbol.
        position_state: Dictionary mapping tickers to position state.
        trade_id_counters: Dictionary mapping tickers to trade ID counters.
    """
    if ticker not in position_state:
        position_state[ticker] = {
            "position_size": 0.0,
            "avg_entry_price": 0.0,
            "first_entry_time": None,
            "side": None,
            "trade_id": None,
        }
        trade_id_counters[ticker] = 0


def _calculate_entry_shares(
    price: float,
    use_account_tracking: bool,
    ticker_accounts: dict,
    trade_percentage: float | None,
    capital_per_trade: float,
    ticker: str,
) -> tuple[float, float]:
    """Calculate shares and capital used for entry.

    Args:
        price: Entry price.
        use_account_tracking: Whether to use account tracking.
        ticker_accounts: Dictionary mapping tickers to account values.
        trade_percentage: Percentage of account to use per trade.
        capital_per_trade: Capital allocated per trade.
        ticker: Ticker symbol.

    Returns:
        Tuple of (shares, capital_used).
    """
    if use_account_tracking:
        current_account = ticker_accounts[ticker]
        trade_capital = current_account * trade_percentage
        shares = math.floor(trade_capital / price)
        capital_used = shares * price
    else:
        shares = capital_per_trade / price
        capital_used = capital_per_trade
    return shares, capital_used


def _process_entry_signal(
    signal: pd.Series,
    position_state: dict,
    trade_id_counters: dict,
    ticker_accounts: dict,
    use_account_tracking: bool,
    trade_percentage: float | None,
    capital_per_trade: float,
) -> None:
    """Process an entry signal and update position state.

    Args:
        signal: Signal row from DataFrame.
        position_state: Dictionary mapping tickers to position state.
        trade_id_counters: Dictionary mapping tickers to trade ID counters.
        ticker_accounts: Dictionary mapping tickers to account values.
        use_account_tracking: Whether to use account tracking.
        trade_percentage: Percentage of account to use per trade.
        capital_per_trade: Capital allocated per trade.
    """
    ticker = signal["ticker"]
    price = signal["price"]
    timestamp = signal["signal_time"]
    side = signal.get("side", "LONG")

    pos = position_state[ticker]

    shares, capital_used = _calculate_entry_shares(
        price,
        use_account_tracking,
        ticker_accounts,
        trade_percentage,
        capital_per_trade,
        ticker,
    )

    if pos["position_size"] == 0:
        trade_id_counters[ticker] += 1
        pos["trade_id"] = trade_id_counters[ticker]
        pos["first_entry_time"] = timestamp
        pos["side"] = side

    pos["position_size"] += shares
    if pos["avg_entry_price"] == 0:
        pos["avg_entry_price"] = price
    else:
        total_cost = (pos["position_size"] - shares) * pos["avg_entry_price"] + capital_used
        pos["avg_entry_price"] = total_cost / pos["position_size"]


def _calculate_exit_shares(
    price: float,
    use_account_tracking: bool,
    ticker_accounts: dict,
    trade_percentage: float | None,
    capital_per_trade: float,
    ticker: str,
) -> float:
    """Calculate shares to exit.

    Args:
        price: Exit price.
        use_account_tracking: Whether to use account tracking.
        ticker_accounts: Dictionary mapping tickers to account values.
        trade_percentage: Percentage of account to use per trade.
        capital_per_trade: Capital allocated per trade.
        ticker: Ticker symbol.

    Returns:
        Number of shares to exit.
    """
    if use_account_tracking:
        current_account = ticker_accounts[ticker]
        trade_capital = current_account * trade_percentage
        exit_shares = math.floor(trade_capital / price)
    else:
        exit_shares = capital_per_trade / price
    return exit_shares


def _calculate_pnl(
    shares_to_close: float, price: float, avg_entry_price: float, side: str
) -> float:
    """Calculate gross PnL for a trade.

    Args:
        shares_to_close: Number of shares to close.
        price: Exit price.
        avg_entry_price: Average entry price.
        side: Trade side ("LONG" or "SHORT").

    Returns:
        Gross PnL value.
    """
    if side == "LONG":
        return shares_to_close * (price - avg_entry_price)
    return shares_to_close * (avg_entry_price - price)


def _create_trade_record(
    ticker: str,
    pos: dict,
    timestamp: pd.Timestamp,
    price: float,
    shares_to_close: float,
    gross_pnl: float,
    gross_pnl_pct: float,
    time_held: float,
    efficiency: float,
    strategy_name: str,
) -> dict:
    """Create a trade record dictionary.

    Args:
        ticker: Ticker symbol.
        pos: Position state dictionary.
        timestamp: Exit timestamp.
        price: Exit price.
        shares_to_close: Number of shares closed.
        gross_pnl: Gross PnL value.
        gross_pnl_pct: Gross PnL percentage.
        time_held: Time held in hours.
        efficiency: Trade efficiency.
        strategy_name: Strategy name.

    Returns:
        Trade record dictionary.
    """
    return {
        "ticker": ticker,
        "entry_time": pos["first_entry_time"] or timestamp,
        "entry_price": pos["avg_entry_price"],
        "exit_time": timestamp,
        "exit_price": price,
        "shares": shares_to_close,
        "gross_pnl": gross_pnl,
        "gross_pnl_pct": gross_pnl_pct,
        "side": pos["side"],
        "status": "CLOSED",
        "strategy": strategy_name,
        "efficiency": efficiency,
        "time_held": time_held,
        "trade_id": pos["trade_id"],
    }


def _reset_position(pos: dict) -> None:
    """Reset position state to empty.

    Args:
        pos: Position state dictionary to reset.
    """
    pos["position_size"] = 0.0
    pos["avg_entry_price"] = 0.0
    pos["first_entry_time"] = None
    pos["side"] = None
    pos["trade_id"] = None


def _process_exit_signal(
    signal: pd.Series,
    position_state: dict,
    matched_trades: list,
    ticker_accounts: dict,
    use_account_tracking: bool,
    trade_percentage: float | None,
    capital_per_trade: float,
    ohlcv_data: pd.DataFrame | None,
    strategy_name: str,
    logger,
) -> None:
    """Process an exit signal and create a trade record.

    Args:
        signal: Signal row from DataFrame.
        position_state: Dictionary mapping tickers to position state.
        matched_trades: List to append matched trades to.
        ticker_accounts: Dictionary mapping tickers to account values.
        use_account_tracking: Whether to use account tracking.
        trade_percentage: Percentage of account to use per trade.
        capital_per_trade: Capital allocated per trade.
        ohlcv_data: Optional OHLCV DataFrame for efficiency calculation.
        strategy_name: Strategy name.
        logger: Logger instance.
    """
    ticker = signal["ticker"]
    price = signal["price"]
    timestamp = signal["signal_time"]

    pos = position_state[ticker]
    if pos["position_size"] == 0:
        return

    exit_shares = _calculate_exit_shares(
        price,
        use_account_tracking,
        ticker_accounts,
        trade_percentage,
        capital_per_trade,
        ticker,
    )

    shares_to_close = min(exit_shares, pos["position_size"])
    capital_used = shares_to_close * pos["avg_entry_price"]

    gross_pnl = _calculate_pnl(shares_to_close, price, pos["avg_entry_price"], pos["side"])
    gross_pnl_pct = (gross_pnl / capital_used) * 100 if capital_used > 0 else 0.0

    time_held = (
        (timestamp - pos["first_entry_time"]).total_seconds() / 3600
        if pos["first_entry_time"]
        else 0.0
    )

    efficiency = calculate_efficiency(
        ticker,
        pos["first_entry_time"] or timestamp,
        timestamp,
        pos["avg_entry_price"],
        price,
        ohlcv_data,
        logger,
    )

    trade_record = _create_trade_record(
        ticker,
        pos,
        timestamp,
        price,
        shares_to_close,
        gross_pnl,
        gross_pnl_pct,
        time_held,
        efficiency,
        strategy_name,
    )
    matched_trades.append(trade_record)

    pos["position_size"] -= shares_to_close

    if pos["position_size"] <= 0:
        _reset_position(pos)

    if use_account_tracking:
        ticker_accounts[ticker] += gross_pnl


def match_trades(
    signals: pd.DataFrame,
    strategy_name: str,
    capital_per_trade: float,
    ohlcv_data: pd.DataFrame | None = None,
    logger=None,
    initial_account_value: float | None = None,
    trade_percentage: float | None = None,
) -> pd.DataFrame:
    """Match trading signals into executed trades.

    Pairs entry signals (buy for LONG, sell for SHORT) with exit signals
    (sell for LONG, buy for SHORT) to create trade records, calculating
    PnL, efficiency, and other metrics.

    Args:
        signals: DataFrame containing trading signals with columns:
            ticker, signal_time, signal_type, price, side.
        strategy_name: Name of the strategy generating signals.
        capital_per_trade: Capital allocated per trade.
        ohlcv_data: Optional OHLCV DataFrame for efficiency calculation.
        logger: Optional logger instance. If not provided, creates a new logger.
        initial_account_value: Optional initial account value for account tracking.
        trade_percentage: Optional percentage of account to use per trade.

    Returns:
        DataFrame containing matched trades with columns:
        entry_time, exit_time, entry_price, exit_price, gross_pnl,
        gross_pnl_pct, efficiency, etc.
    """
    logger = logger or get_logger("TradeMatching")
    if signals.empty:
        logger.warning("No signals to match")
        return pd.DataFrame()

    signals = signals.sort_values(["ticker", "signal_time"])
    matched_trades = []
    position_state = {}
    trade_id_counters = {}

    ticker_accounts = {}
    use_account_tracking = initial_account_value is not None and trade_percentage is not None
    if use_account_tracking:
        for ticker in signals["ticker"].unique():
            ticker_accounts[ticker] = initial_account_value

    for _, signal in signals.iterrows():
        ticker = signal["ticker"]
        signal_type = signal["signal_type"]
        side = signal.get("side", "LONG")

        _initialize_position_state(ticker, position_state, trade_id_counters)

        is_entry = (side == "LONG" and signal_type == "buy") or (
            side == "SHORT" and signal_type == "sell"
        )
        is_exit = (side == "LONG" and signal_type == "sell") or (
            side == "SHORT" and signal_type == "buy"
        )

        if is_entry:
            _process_entry_signal(
                signal,
                position_state,
                trade_id_counters,
                ticker_accounts,
                use_account_tracking,
                trade_percentage,
                capital_per_trade,
            )
        elif is_exit:
            _process_exit_signal(
                signal,
                position_state,
                matched_trades,
                ticker_accounts,
                use_account_tracking,
                trade_percentage,
                capital_per_trade,
                ohlcv_data,
                strategy_name,
                logger,
            )

    total_unmatched = sum(1 for pos in position_state.values() if pos["position_size"] > 0)
    if total_unmatched > 0:
        logger.debug(f"{total_unmatched} open positions remain unmatched")

    if not matched_trades:
        logger.warning("No trades could be matched")
        return pd.DataFrame()

    trades_df = pd.DataFrame(matched_trades)
    logger.debug(f"Matched {len(trades_df)} completed trades")
    return trades_df
