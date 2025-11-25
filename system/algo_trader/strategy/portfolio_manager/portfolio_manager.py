from typing import Any

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.strategy.portfolio_manager.rules.base import (
    PortfolioPosition,
    PortfolioRuleContext,
    PortfolioRulePipeline,
    PortfolioState,
)


class PortfolioManager:
    def __init__(
        self,
        pipeline: PortfolioRulePipeline,
        initial_account_value: float,
        settlement_lag_trading_days: int = 2,
        logger=None,
    ) -> None:
        self.pipeline = pipeline
        self.initial_account_value = initial_account_value
        self.settlement_lag_trading_days = settlement_lag_trading_days
        self.logger = logger or get_logger(self.__class__.__name__)

    def apply(
        self,
        executions: pd.DataFrame,
        ohlcv_by_ticker: dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        if executions.empty:
            return executions

        trading_days = self._build_trading_calendar(ohlcv_by_ticker)
        sort_cols = ["signal_time", "ticker"]
        if "strategy" in executions.columns:
            sort_cols.append("strategy")
        df = executions.sort_values(sort_cols).copy()

        state = PortfolioState(cash_available=self.initial_account_value)
        approved_rows: list[dict[str, Any]] = []
        current_day = None

        for _, row in df.iterrows():
            ts = pd.to_datetime(row["signal_time"]).tz_convert("UTC")
            trading_day = ts.normalize()

            if current_day is None or trading_day > current_day:
                current_day = trading_day
                self._release_settlements(state, current_day)

            ticker = row["ticker"]
            side = row.get("side", "LONG")
            raw_action = row.get("action")
            price = float(row["price"])
            shares = float(row["shares"])

            is_close = raw_action in {"sell_to_close", "buy_to_close"}
            is_open = raw_action in {"buy_to_open", "sell_to_open"}

            pos = state.positions.setdefault(ticker, PortfolioPosition())

            ctx = PortfolioRuleContext(
                signal=row.to_dict(),
                portfolio_state=state,
                ohlcv_by_ticker=ohlcv_by_ticker,
            )

            if is_close:
                self._apply_close(state, pos, row, trading_days, price, shares)
                approved_rows.append(row.to_dict())
                continue

            if is_open:
                allow, max_shares, reason = self.pipeline.decide_entry(ctx)
                if not allow:
                    continue

                eff_shares = shares if max_shares is None else min(shares, max_shares)
                required_capital = eff_shares * price
                if required_capital <= 0.0 or required_capital > state.cash_available:
                    continue

                state.cash_available -= required_capital
                pos.shares += eff_shares
                pos.side = side
                if pos.avg_entry_price == 0.0:
                    pos.avg_entry_price = price
                else:
                    total_cost = (
                        (pos.shares - eff_shares) * pos.avg_entry_price
                        + eff_shares * price
                    )
                    pos.avg_entry_price = total_cost / pos.shares

                row_dict = row.to_dict()
                row_dict["shares"] = eff_shares
                if reason is not None:
                    row_dict["portfolio_reason"] = reason
                approved_rows.append(row_dict)
                continue

        return pd.DataFrame(approved_rows)

    def _build_trading_calendar(
        self, ohlcv_by_ticker: dict[str, pd.DataFrame]
    ) -> list[pd.Timestamp]:
        all_days: set[pd.Timestamp] = set()
        for df in ohlcv_by_ticker.values():
            if df is None or df.empty:
                continue
            days = df.index.normalize().unique()
            all_days.update(days)
        return sorted(all_days)

    def _release_settlements(self, state: PortfolioState, current_day: pd.Timestamp) -> None:
        to_release = [d for d in state.pending_settlements.keys() if d <= current_day]
        for d in to_release:
            state.cash_available += state.pending_settlements.pop(d)

    def _apply_close(
        self,
        state: PortfolioState,
        pos: PortfolioPosition,
        row: pd.Series,
        trading_days: list[pd.Timestamp],
        price: float,
        shares: float,
    ) -> None:
        if pos.shares <= 0:
            return

        close_shares = min(shares, pos.shares)
        pos.shares -= close_shares
        proceeds = close_shares * price

        ts = pd.to_datetime(row["signal_time"]).tz_convert("UTC")
        trade_day = ts.normalize()

        try:
            i = trading_days.index(trade_day)
        except ValueError:
            return

        j = min(i + self.settlement_lag_trading_days, len(trading_days) - 1)
        settle_day = trading_days[j]
        state.pending_settlements[settle_day] = (
            state.pending_settlements.get(settle_day, 0.0) + proceeds
        )

        if pos.shares <= 0:
            pos.shares = 0.0
            pos.avg_entry_price = 0.0
            pos.side = None

