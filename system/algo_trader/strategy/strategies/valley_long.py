import json
from typing import Any

import pandas as pd

from infrastructure.influxdb.influxdb import BatchWriteConfig
from system.algo_trader.strategy.base import BaseStrategy
from system.algo_trader.strategy.utils.studies.support_resistance.find_peaks import FindPeaks
from system.algo_trader.strategy.utils.studies.support_resistance.find_valleys import FindValleys


class ValleyLong(BaseStrategy):
    strategy_type = "LONG"

    def __init__(
        self,
        valley_distance: int = 50,
        valley_prominence: float | None = 2.0,
        valley_height: float | tuple[float, float] | None = None,
        valley_width: int | None = None,
        valley_threshold: float | None = None,
        peak_distance: int = 50,
        peak_prominence: float | None = 2.0,
        peak_height: float | tuple[float, float] | None = None,
        peak_width: int | None = None,
        peak_threshold: float | None = None,
        nearness_threshold: float = 0.5,
        sell_nearness_threshold: float | None = None,
        min_confidence: float = 0.0,
        database: str | None = None,
        write_config: BatchWriteConfig | None = None,
        use_threading: bool = False,
        config: Any = None,
        thread_config: Any = None,
    ):
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError(f"min_confidence must be in [0.0, 1.0], got {min_confidence}")
        if nearness_threshold <= 0.0:
            raise ValueError(f"nearness_threshold must be > 0.0, got {nearness_threshold}")

        strategy_args = {
            "valley_distance": valley_distance,
            "valley_prominence": valley_prominence,
            "valley_height": valley_height,
            "valley_width": valley_width,
            "valley_threshold": valley_threshold,
            "peak_distance": peak_distance,
            "peak_prominence": peak_prominence,
            "peak_height": peak_height,
            "peak_width": peak_width,
            "peak_threshold": peak_threshold,
            "nearness_threshold": nearness_threshold,
            "sell_nearness_threshold": sell_nearness_threshold,
        }

        init_kwargs = {
            "database": database,
            "use_threading": use_threading,
            "config": config,
            "thread_config": thread_config,
            "strategy_args": strategy_args,
        }
        if write_config is not None:
            init_kwargs["write_config"] = write_config

        super().__init__(**init_kwargs)

        self.valley_distance = valley_distance
        self.valley_prominence = valley_prominence
        self.valley_height = valley_height
        self.valley_width = valley_width
        self.valley_threshold = valley_threshold
        self.peak_distance = peak_distance
        self.peak_prominence = peak_prominence
        self.peak_height = peak_height
        self.peak_width = peak_width
        self.peak_threshold = peak_threshold
        self.nearness_threshold = nearness_threshold
        self.sell_nearness_threshold = sell_nearness_threshold if sell_nearness_threshold is not None else nearness_threshold * 0.4
        self.min_confidence = min_confidence

        self.valley_study = FindValleys(logger=self.logger)
        self.peak_study = FindPeaks(logger=self.logger)

        self.logger.debug(
            f"ValleyLong initialized: valley_distance={valley_distance}, "
            f"peak_distance={peak_distance}, nearness_threshold={nearness_threshold}, "
            f"sell_nearness_threshold={self.sell_nearness_threshold}, min_confidence={min_confidence}"
        )

    def buy(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        valleys_df = self._compute_valleys(ohlcv_data, ticker)
        if valleys_df is None or valleys_df.empty:
            return pd.DataFrame()

        all_valleys = self._extract_all_values(valleys_df, "valley")
        if not all_valleys:
            return pd.DataFrame()

        buy_signals = []
        prices = ohlcv_data["close"]
        
        for idx in ohlcv_data.index:
            price = prices.loc[idx]
            valley_match = self._find_near_value(price, all_valleys)
            if valley_match is not None:
                if self._is_coming_down(prices, idx, valley_match):
                    signal = self._create_buy_signal(idx, ohlcv_data, price, valley_match)
                    buy_signals.append(signal)

        if not buy_signals:
            self.logger.debug(f"No buy signals detected for {ticker}")
            return pd.DataFrame()

        signals_df = pd.DataFrame(buy_signals)
        signals_df = signals_df.set_index("timestamp")
        signals_df.index.name = None

        self.logger.debug(f"Generated {len(signals_df)} buy signals for {ticker}")
        return signals_df

    def sell(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        peaks_df = self._compute_peaks(ohlcv_data, ticker)
        valleys_df = self._compute_valleys(ohlcv_data, ticker)
        if peaks_df is None and valleys_df is None:
            return pd.DataFrame()

        all_peaks = self._extract_all_values(peaks_df, "peak") if peaks_df is not None and not peaks_df.empty else []
        all_valleys = self._extract_all_values(valleys_df, "valley") if valleys_df is not None and not valleys_df.empty else []

        if not all_peaks and not all_valleys:
            return pd.DataFrame()

        sell_signals = []
        most_recent_valley = None
        prices = ohlcv_data["close"]

        for idx in ohlcv_data.index:
            price = prices.loc[idx]
            signal = None

            if all_peaks:
                peak_match = self._find_near_value_sell(price, all_peaks)
                if peak_match is not None:
                    if self._is_coming_up(prices, idx, peak_match):
                        signal = self._create_sell_signal(idx, ohlcv_data, price, peak_match, "peak")

            if signal is None and all_valleys:
                valley_match = self._find_near_value_sell(price, all_valleys)
                if valley_match is not None:
                    if most_recent_valley is None or abs(valley_match - most_recent_valley) > 0.0001:
                        if self._is_coming_up(prices, idx, valley_match):
                            signal = self._create_sell_signal(idx, ohlcv_data, price, valley_match, "valley")
                    most_recent_valley = valley_match

            if signal is not None:
                sell_signals.append(signal)

        if not sell_signals:
            self.logger.debug(f"No sell signals detected for {ticker}")
            return pd.DataFrame()

        signals_df = pd.DataFrame(sell_signals)
        signals_df = signals_df.set_index("timestamp")
        signals_df.index.name = None

        self.logger.debug(f"Generated {len(signals_df)} sell signals for {ticker}")
        return signals_df

    def generate_signals(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        if ohlcv_data is None or ohlcv_data.empty:
            return pd.DataFrame()

        buy_signals = self.buy(ohlcv_data, ticker)
        sell_signals = self.sell(ohlcv_data, ticker)

        all_signals = []
        if not buy_signals.empty:
            buy_signals["signal_type"] = "buy"
            all_signals.append(buy_signals)
        if not sell_signals.empty:
            sell_signals["signal_type"] = "sell"
            all_signals.append(sell_signals)

        if not all_signals:
            return pd.DataFrame()

        combined = pd.concat(all_signals).sort_index()

        if self.min_confidence > 0.0 and "confidence" in combined.columns:
            combined = combined[combined["confidence"] >= self.min_confidence]

        return combined

    def add_strategy_arguments(self, parser):
        parser.add_argument(
            "--valley-distance",
            type=int,
            default=50,
            help="Minimum distance between valleys (default: 50)",
        )
        parser.add_argument(
            "--valley-prominence",
            type=float,
            default=2.0,
            help="Minimum prominence for valley detection as percentage (default: 2.0%%)",
        )
        parser.add_argument(
            "--valley-height",
            type=float,
            default=None,
            help="Height constraint for valley detection as percentage (default: None)",
        )
        parser.add_argument(
            "--valley-width",
            type=int,
            default=None,
            help="Width constraint for valley detection in periods (default: None)",
        )
        parser.add_argument(
            "--valley-threshold",
            type=float,
            default=None,
            help="Threshold for valley detection as percentage (default: None)",
        )
        parser.add_argument(
            "--peak-distance",
            type=int,
            default=50,
            help="Minimum distance between peaks (default: 50)",
        )
        parser.add_argument(
            "--peak-prominence",
            type=float,
            default=2.0,
            help="Minimum prominence for peak detection as percentage (default: 2.0%%)",
        )
        parser.add_argument(
            "--peak-height",
            type=float,
            default=None,
            help="Height constraint for peak detection as percentage (default: None)",
        )
        parser.add_argument(
            "--peak-width",
            type=int,
            default=None,
            help="Width constraint for peak detection in periods (default: None)",
        )
        parser.add_argument(
            "--peak-threshold",
            type=float,
            default=None,
            help="Threshold for peak detection as percentage (default: None)",
        )
        parser.add_argument(
            "--nearness-threshold",
            type=float,
            default=0.5,
            help="Percentage threshold for 'near' a valley/peak for buy signals (default: 0.5)",
        )
        parser.add_argument(
            "--sell-nearness-threshold",
            type=float,
            default=None,
            help="Percentage threshold for 'near' a valley/peak for sell signals (default: 40%% of buy threshold)",
        )
        parser.add_argument(
            "--min-confidence",
            type=float,
            default=0.0,
            help="Minimum confidence threshold (default: 0.0)",
        )

    def _compute_valleys(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame | None:
        kwargs = {}
        if self.valley_distance is not None:
            kwargs["distance"] = self.valley_distance
        
        needs_avg_price = (
            self.valley_prominence is not None
            or self.valley_height is not None
            or self.valley_threshold is not None
        )
        avg_price = ohlcv_data["close"].mean() if needs_avg_price else None
        
        if self.valley_prominence is not None:
            kwargs["prominence"] = avg_price * (self.valley_prominence / 100.0)
        if self.valley_height is not None:
            if isinstance(self.valley_height, tuple):
                kwargs["height"] = (
                    avg_price * (self.valley_height[0] / 100.0),
                    avg_price * (self.valley_height[1] / 100.0),
                )
            else:
                kwargs["height"] = avg_price * (self.valley_height / 100.0)
        if self.valley_width is not None:
            kwargs["width"] = self.valley_width
        if self.valley_threshold is not None:
            if isinstance(self.valley_threshold, tuple):
                kwargs["threshold"] = (
                    avg_price * (self.valley_threshold[0] / 100.0),
                    avg_price * (self.valley_threshold[1] / 100.0),
                )
            else:
                kwargs["threshold"] = avg_price * (self.valley_threshold / 100.0)

        return self.valley_study.compute(ohlcv_data=ohlcv_data, ticker=ticker, column="close", **kwargs)

    def _compute_peaks(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame | None:
        kwargs = {}
        if self.peak_distance is not None:
            kwargs["distance"] = self.peak_distance
        
        needs_avg_price = (
            self.peak_prominence is not None
            or self.peak_height is not None
            or self.peak_threshold is not None
        )
        avg_price = ohlcv_data["close"].mean() if needs_avg_price else None
        
        if self.peak_prominence is not None:
            kwargs["prominence"] = avg_price * (self.peak_prominence / 100.0)
        if self.peak_height is not None:
            if isinstance(self.peak_height, tuple):
                kwargs["height"] = (
                    avg_price * (self.peak_height[0] / 100.0),
                    avg_price * (self.peak_height[1] / 100.0),
                )
            else:
                kwargs["height"] = avg_price * (self.peak_height / 100.0)
        if self.peak_width is not None:
            kwargs["width"] = self.peak_width
        if self.peak_threshold is not None:
            if isinstance(self.peak_threshold, tuple):
                kwargs["threshold"] = (
                    avg_price * (self.peak_threshold[0] / 100.0),
                    avg_price * (self.peak_threshold[1] / 100.0),
                )
            else:
                kwargs["threshold"] = avg_price * (self.peak_threshold / 100.0)

        return self.peak_study.compute(ohlcv_data=ohlcv_data, ticker=ticker, column="close", **kwargs)

    def _extract_all_values(self, df: pd.DataFrame, prefix: str) -> list[float]:
        values = []
        for col in df.columns:
            if col.startswith(prefix):
                col_values = df[col].dropna().unique()
                values.extend(col_values.tolist())
        return sorted(set(values))

    def _find_near_value(self, price: float, target_values: list[float]) -> float | None:
        if not target_values:
            return None
        threshold_pct = self.nearness_threshold / 100.0
        for target_value in target_values:
            if target_value == 0.0:
                continue
            pct_diff = abs((price - target_value) / target_value)
            if pct_diff <= threshold_pct:
                return target_value
        return None

    def _find_near_value_sell(self, price: float, target_values: list[float]) -> float | None:
        if not target_values:
            return None
        threshold_pct = self.sell_nearness_threshold / 100.0
        for target_value in target_values:
            if target_value == 0.0:
                continue
            pct_diff = abs((price - target_value) / target_value)
            if pct_diff <= threshold_pct:
                return target_value
        return None

    def _is_coming_down(self, prices: pd.Series, current_idx: pd.Timestamp, valley_value: float, lookback_periods: int = 5) -> bool:
        try:
            current_pos = prices.index.get_loc(current_idx)
            if current_pos < lookback_periods:
                return False
            
            current_price = prices.loc[current_idx]
            recent_prices = prices.iloc[current_pos - lookback_periods:current_pos]
            
            if len(recent_prices) == 0:
                return False
            
            avg_recent_price = recent_prices.mean()
            return current_price < avg_recent_price and avg_recent_price > valley_value
        except (KeyError, IndexError):
            return False

    def _is_coming_up(self, prices: pd.Series, current_idx: pd.Timestamp, target_value: float, lookback_periods: int = 5) -> bool:
        try:
            current_pos = prices.index.get_loc(current_idx)
            if current_pos < lookback_periods:
                return False
            
            current_price = prices.loc[current_idx]
            recent_prices = prices.iloc[current_pos - lookback_periods:current_pos]
            
            if len(recent_prices) == 0:
                return False
            
            avg_recent_price = recent_prices.mean()
            return current_price > avg_recent_price and avg_recent_price < target_value
        except (KeyError, IndexError):
            return False

    def _calculate_confidence(self, price: float, target_value: float) -> float:
        if target_value == 0.0:
            return 0.0
        pct_diff = abs((price - target_value) / target_value)
        threshold_pct = self.nearness_threshold / 100.0
        confidence = max(0.0, 1.0 - (pct_diff / threshold_pct))
        return round(min(1.0, confidence), 4)

    def _create_buy_signal(
        self, timestamp: pd.Timestamp, ohlcv_data: pd.DataFrame, price: float, valley_value: float
    ) -> dict[str, Any]:
        confidence = self._calculate_confidence(price, valley_value)
        metadata = {
            "valley_value": round(valley_value, 4),
            "price_diff": round(price - valley_value, 4),
            "price_diff_pct": round(((price - valley_value) / valley_value) * 100, 4),
            "nearness_threshold": self.nearness_threshold,
        }
        return {
            "timestamp": timestamp,
            "price": round(price, 4),
            "confidence": confidence,
            "metadata": json.dumps(metadata),
        }

    def _create_sell_signal(
        self,
        timestamp: pd.Timestamp,
        ohlcv_data: pd.DataFrame,
        price: float,
        target_value: float,
        signal_source: str,
    ) -> dict[str, Any]:
        confidence = self._calculate_confidence(price, target_value)
        metadata = {
            "target_value": round(target_value, 4),
            "signal_source": signal_source,
            "price_diff": round(price - target_value, 4),
            "price_diff_pct": round(((price - target_value) / target_value) * 100, 4),
            "nearness_threshold": self.nearness_threshold,
        }
        return {
            "timestamp": timestamp,
            "price": round(price, 4),
            "confidence": confidence,
            "metadata": json.dumps(metadata),
        }

