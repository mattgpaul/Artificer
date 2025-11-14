from datetime import datetime, timezone

import pandas as pd

from infrastructure.logging.logger import get_logger
from system.algo_trader.influx.market_data_influx import MarketDataInflux


class ResultsWriter:
    def __init__(self, database: str = "algo-trader-trading-journal"):
        self.database = database
        self.influx_client = MarketDataInflux(database=database)
        self.logger = get_logger(self.__class__.__name__)

    def write_trades(
        self,
        trades: pd.DataFrame,
        strategy_name: str,
        backtest_id: str | None = None,
    ) -> bool:
        if trades.empty:
            self.logger.warning("No trades to write")
            return True

        table_name = strategy_name

        records = []
        for _, trade in trades.iterrows():
            status = "WIN" if trade.get("gross_pnl", 0) > 0 else "LOSS"
            net_pnl = trade.get("net_pnl", trade.get("gross_pnl", 0))
            net_pnl_pct = trade.get("net_pnl_pct", trade.get("gross_pnl_pct", 0))

            record = {
                "datetime": int(trade["exit_time"].timestamp() * 1000),
                "status": status,
                "date": trade["exit_time"].strftime("%b %d, %Y").upper(),
                "symbol": trade["ticker"],
                "entry": round(trade["entry_price"], 2),
                "exit": round(trade["exit_price"], 2),
                "size": round(trade["shares"], 4),
                "side": trade["side"],
                "return_dollar": round(net_pnl, 2),
                "return_pct": round(net_pnl_pct, 2),
                "setups": strategy_name,
                "efficiency": round(trade.get("efficiency", 0.0), 2),
                "entry_time": int(trade["entry_time"].timestamp() * 1000),
                "gross_pnl": round(trade.get("gross_pnl", 0), 2),
                "gross_pnl_pct": round(trade.get("gross_pnl_pct", 0), 2),
                "commission": round(trade.get("commission", 0), 2),
                "strategy": strategy_name,
            }

            if backtest_id:
                record["backtest_id"] = backtest_id

            records.append(record)

        try:
            df = pd.DataFrame(records)
            df["datetime"] = pd.to_datetime(df["datetime"], unit="ms", utc=True)
            df = df.set_index("datetime")

            df["ticker"] = df["symbol"]

            self.influx_client.client.write(
                df, data_frame_measurement_name=table_name, data_frame_tag_columns=["ticker", "strategy"]
            )

            self.logger.info(f"Wrote {len(records)} trades to {self.database}.{table_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to write trades: {e}")
            return False

    def write_metrics(
        self,
        metrics: dict,
        strategy_name: str,
        backtest_id: str | None = None,
    ) -> bool:
        table_name = f"{strategy_name}_summary"

        record = {
            "datetime": int(datetime.now(timezone.utc).timestamp() * 1000),
            "total_trades": metrics.get("total_trades", 0),
            "total_profit": round(metrics.get("total_profit", 0), 2),
            "total_profit_pct": round(metrics.get("total_profit_pct", 0), 2),
            "max_drawdown": round(metrics.get("max_drawdown", 0), 2),
            "sharpe_ratio": round(metrics.get("sharpe_ratio", 0), 4),
            "avg_efficiency": round(metrics.get("avg_efficiency", 0), 2),
            "avg_return_pct": round(metrics.get("avg_return_pct", 0), 2),
            "avg_time_held": round(metrics.get("avg_time_held", 0), 2),
            "win_rate": round(metrics.get("win_rate", 0), 2),
            "strategy": strategy_name,
        }

        if backtest_id:
            record["backtest_id"] = backtest_id

        try:
            df = pd.DataFrame([record])
            df["datetime"] = pd.to_datetime(df["datetime"], unit="ms", utc=True)
            df = df.set_index("datetime")

            self.influx_client.client.write(
                df, data_frame_measurement_name=table_name, data_frame_tag_columns=["strategy"]
            )

            self.logger.info(f"Wrote metrics to {self.database}.{table_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to write metrics: {e}")
            return False

    def close(self) -> None:
        self.influx_client.close()

