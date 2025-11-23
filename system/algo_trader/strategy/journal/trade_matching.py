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
    ticker = signal["ticker"]
    price = signal["price"]
    timestamp = signal["signal_time"]
    side = signal.get("side", "LONG")

    pos = position_state[ticker]

    if "shares" in signal and pd.notna(signal["shares"]):
        shares = float(signal["shares"])
        capital_used = shares * price
    else:
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
    reason: str | None,
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
    record = {
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
    if reason is not None:
        record["exit_reason"] = reason
    return record


def _match_trades_raw(
    signals: pd.DataFrame,
    strategy_name: str,
    capital_per_trade: float,
    ohlcv_data: pd.DataFrame | None,
    logger,
) -> pd.DataFrame:
    signals = signals.sort_values(["ticker", "signal_time"])
    matched_trades = []
    entry_queues: dict[str, list] = {}
    trade_id_counters: dict[str, int] = {}

    for _, signal in signals.iterrows():
        ticker = signal["ticker"]
        signal_type = signal["signal_type"]
        side = signal.get("side", "LONG")
        price = signal["price"]
        timestamp = signal["signal_time"]

        if ticker not in entry_queues:
            entry_queues[ticker] = []
            trade_id_counters[ticker] = 0

        is_entry = (side == "LONG" and signal_type == "buy") or (
            side == "SHORT" and signal_type == "sell"
        )
        is_exit = (side == "LONG" and signal_type == "sell") or (
            side == "SHORT" and signal_type == "buy"
        )

        if is_entry:
            shares = capital_per_trade / price
            trade_id_counters[ticker] += 1
            entry_queues[ticker].append(
                {
                    "entry_time": timestamp,
                    "entry_price": price,
                    "shares": shares,
                    "side": side,
                    "trade_id": trade_id_counters[ticker],
                }
            )
        elif is_exit:
            queue = entry_queues[ticker]
            if queue:
                entry = queue.pop(0)
                exit_time = timestamp
                exit_price = price
                shares = entry["shares"]

                gross_pnl = _calculate_pnl(shares, exit_price, entry["entry_price"], entry["side"])
                capital_used = shares * entry["entry_price"]
                gross_pnl_pct = (gross_pnl / capital_used) * 100 if capital_used > 0 else 0.0

                time_held = (exit_time - entry["entry_time"]).total_seconds() / 3600

                efficiency = calculate_efficiency(
                    ticker,
                    entry["entry_time"],
                    exit_time,
                    entry["entry_price"],
                    exit_price,
                    ohlcv_data,
                    logger,
                )

                trade_record = {
                    "ticker": ticker,
                    "entry_time": entry["entry_time"],
                    "entry_price": entry["entry_price"],
                    "exit_time": exit_time,
                    "exit_price": exit_price,
                    "shares": shares,
                    "gross_pnl": gross_pnl,
                    "gross_pnl_pct": gross_pnl_pct,
                    "side": entry["side"],
                    "status": "CLOSED",
                    "strategy": strategy_name,
                    "efficiency": efficiency,
                    "time_held": time_held,
                    "trade_id": entry["trade_id"],
                }
                matched_trades.append(trade_record)

    if not matched_trades:
        logger.warning("No trades could be matched")
        return pd.DataFrame()

    trades_df = pd.DataFrame(matched_trades)
    logger.debug(f"Matched {len(trades_df)} completed trades (raw mode)")
    return trades_df


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
    close_full_on_exit: bool = False,
) -> None:
    ticker = signal["ticker"]
    price = signal["price"]
    timestamp = signal["signal_time"]

    pos = position_state[ticker]
    if pos["position_size"] == 0:
        return

    if "shares" in signal and pd.notna(signal["shares"]):
        shares_to_close = float(signal["shares"])
        shares_to_close = min(shares_to_close, pos["position_size"])
    elif close_full_on_exit:
        shares_to_close = pos["position_size"]
    else:
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
        signal.get("reason"),
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
    mode: str = "pm_managed",
    pm_config: dict | None = None,
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
        mode: Position management mode. Defaults to "pm_managed".
        pm_config: Optional position manager configuration dictionary.

    Returns:
        DataFrame containing matched trades with columns:
        entry_time, exit_time, entry_price, exit_price, gross_pnl,
        gross_pnl_pct, efficiency, etc.
    """
    logger = logger or get_logger("TradeMatching")
    if signals.empty:
        logger.warning("No signals to match")
        return pd.DataFrame()

    if mode == "raw":
        return _match_trades_raw(signals, strategy_name, capital_per_trade, ohlcv_data, logger)

    signals = signals.sort_values(["ticker", "signal_time"])
    matched_trades = []
    position_state = {}
    trade_id_counters = {}

    ticker_accounts = {}
    use_account_tracking = initial_account_value is not None and trade_percentage is not None
    if use_account_tracking:
        for ticker in signals["ticker"].unique():
            ticker_accounts[ticker] = initial_account_value

    close_full_on_exit = False
    if pm_config and pm_config.get("close_full_on_exit", False):
        close_full_on_exit = True

    use_pm_actions = mode == "pm_managed" and "action" in signals.columns

    for _, signal in signals.iterrows():
        ticker = signal["ticker"]
        _initialize_position_state(ticker, position_state, trade_id_counters)

        if use_pm_actions:
            action = signal.get("action")
            if action not in {"open", "scale_in", "scale_out", "close"}:
                continue

            if "shares" not in signal or pd.isna(signal["shares"]):
                logger.warning(
                    "pm_managed mode requires explicit 'shares' on signals; "
                    f"skipping signal for {ticker} at {signal.get('signal_time')}"
                )
                continue

            if action in {"open", "scale_in"}:
                _process_entry_signal(
                    signal,
                    position_state,
                    trade_id_counters,
                    ticker_accounts,
                    use_account_tracking,
                    trade_percentage,
                    capital_per_trade,
                )
            elif action in {"scale_out", "close"}:
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
                    close_full_on_exit,
                )
            continue

        signal_type = signal["signal_type"]
        side = signal.get("side", "LONG")

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
                close_full_on_exit,
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
