"""Simple Moving Average (SMA) crossover trading strategy.

This strategy generates buy/sell signals based on the crossover of two simple
moving averages (SMA). A buy signal occurs when the short-period SMA crosses
above the long-period SMA (bullish crossover), and a sell signal occurs when
the short-period SMA crosses below the long-period SMA (bearish crossover).

Typical usage:
    >>> strategy = SMACrossoverStrategy(short_window=10, long_window=20)
    >>> signals = strategy.run_strategy('AAPL', start_time='2024-01-01')
"""

import json
from typing import Any

import pandas as pd

from infrastructure.influxdb.influxdb import BatchWriteConfig
from system.algo_trader.strategy.base import BaseStrategy


class SMACrossoverStrategy(BaseStrategy):
    """SMA crossover strategy for generating buy/sell trading signals.

    This strategy detects crossover points between two simple moving averages:
    - Buy signal: Short-period SMA crosses above long-period SMA (bullish)
    - Sell signal: Short-period SMA crosses below long-period SMA (bearish)

    Confidence scores are calculated based on the strength of the crossover,
    measured by the percentage difference between the two SMAs at the crossover point.

    Attributes:
        short_window: Number of periods for the short-term SMA (default: 10).
        long_window: Number of periods for the long-term SMA (default: 20).
        min_confidence: Minimum crossover strength to generate a signal (default: 0.0).
    """

    def __init__(  # noqa: PLR0913
        self,
        short_window: int = 10,
        long_window: int = 20,
        min_confidence: float = 0.0,
        database: str = "algo-trader-database",
        write_config: BatchWriteConfig | None = None,
        use_threading: bool = False,
        config: Any = None,
    ):
        """Initialize SMA crossover strategy.

        Args:
            short_window: Period for short-term SMA (must be less than long_window).
            long_window: Period for long-term SMA (must be greater than short_window).
            min_confidence: Minimum confidence threshold for signal generation (0.0-1.0).
            database: InfluxDB database name for signal persistence.
            write_config: Optional batch write configuration for InfluxDB.
            use_threading: Enable parallel processing for multiple tickers.
            config: Optional InfluxDB configuration override.

        Raises:
            ValueError: If short_window >= long_window or parameters are invalid.
        """
        if short_window >= long_window:
            raise ValueError(
                f"short_window ({short_window}) must be less than long_window ({long_window})"
            )
        if short_window < 2:
            raise ValueError(f"short_window must be at least 2, got {short_window}")
        if min_confidence < 0.0 or min_confidence > 1.0:
            raise ValueError(f"min_confidence must be in [0.0, 1.0], got {min_confidence}")

        strategy_name = f"sma_crossover_{short_window}_{long_window}"

        # Use default write_config from base class if not provided
        init_kwargs = {
            "strategy_name": strategy_name,
            "database": database,
            "use_threading": use_threading,
            "config": config,
        }
        if write_config is not None:
            init_kwargs["write_config"] = write_config

        super().__init__(**init_kwargs)

        self.short_window = short_window
        self.long_window = long_window
        self.min_confidence = min_confidence

        self.logger.info(
            f"SMA Crossover initialized: short={short_window}, "
            f"long={long_window}, min_confidence={min_confidence}"
        )

    def generate_signals(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Generate buy/sell signals from SMA crossover analysis.

        Calculates short and long-period SMAs on close prices, detects crossover
        points, and generates signals with confidence scores based on crossover strength.

        Args:
            ohlcv_data: DataFrame with OHLCV data indexed by datetime.
                       Must contain 'close' column and at least long_window rows.
            ticker: Stock ticker symbol being analyzed.

        Returns:
            DataFrame with columns:
                - signal_type: 'buy' (bullish crossover) or 'sell' (bearish crossover)
                - price: Close price at the crossover point
                - confidence: Normalized crossover strength (0.0-1.0)
                - metadata: JSON string containing SMA values and crossover details

            Indexed by datetime of signal generation. Returns empty DataFrame if:
            - Insufficient data for long_window calculation
            - No crossovers detected
            - All signals below min_confidence threshold

        Example:
            >>> signals = strategy.generate_signals(ohlcv_df, 'AAPL')
            >>> # Typical output:
            >>> #                      signal_type   price  confidence metadata
            >>> # 2024-01-15 10:00:00  buy          150.25  0.75       {...}
            >>> # 2024-02-20 14:30:00  sell         148.50  0.82       {...}
        """
        if ohlcv_data is None or ohlcv_data.empty:
            self.logger.warning(f"No OHLCV data provided for {ticker}")
            return pd.DataFrame()

        if "close" not in ohlcv_data.columns:
            self.logger.error(f"OHLCV data for {ticker} missing 'close' column")
            return pd.DataFrame()

        if len(ohlcv_data) < self.long_window:
            self.logger.warning(
                f"Insufficient data for {ticker}: {len(ohlcv_data)} rows "
                f"(need at least {self.long_window} for SMA calculation)"
            )
            return pd.DataFrame()

        # Calculate simple moving averages
        sma_short = ohlcv_data["close"].rolling(window=self.short_window).mean()
        sma_long = ohlcv_data["close"].rolling(window=self.long_window).mean()

        # Detect crossovers by comparing current and previous positions
        # bullish: short crosses above long (was below, now above)
        # bearish: short crosses below long (was above, now below)
        previous_diff = (sma_short - sma_long).shift(1)
        current_diff = sma_short - sma_long

        bullish_crossover = (previous_diff < 0) & (current_diff > 0)
        bearish_crossover = (previous_diff > 0) & (current_diff < 0)

        # Extract crossover points
        signals = []

        for idx in ohlcv_data.index:
            if bullish_crossover.loc[idx]:
                signal = self._create_signal(
                    idx, "buy", ohlcv_data, sma_short, sma_long, current_diff
                )
                if signal:
                    signals.append(signal)

            elif bearish_crossover.loc[idx]:
                signal = self._create_signal(
                    idx, "sell", ohlcv_data, sma_short, sma_long, current_diff
                )
                if signal:
                    signals.append(signal)

        if not signals:
            self.logger.info(f"No crossover signals detected for {ticker}")
            return pd.DataFrame()

        # Convert to DataFrame with datetime index
        signals_df = pd.DataFrame(signals)
        signals_df = signals_df.set_index("timestamp")
        signals_df.index.name = None  # Remove index name for consistency

        self.logger.info(
            f"Generated {len(signals_df)} signals for {ticker}: "
            f"{(signals_df['signal_type'] == 'buy').sum()} buys, "
            f"{(signals_df['signal_type'] == 'sell').sum()} sells"
        )

        return signals_df

    def _create_signal(  # noqa: PLR0913
        self,
        timestamp: pd.Timestamp,
        signal_type: str,
        ohlcv_data: pd.DataFrame,
        sma_short: pd.Series,
        sma_long: pd.Series,
        diff: pd.Series,
    ) -> dict[str, Any] | None:
        """Create a signal dictionary with confidence and metadata.

        Args:
            timestamp: Datetime of the crossover event.
            signal_type: 'buy' or 'sell'.
            ohlcv_data: Original OHLCV DataFrame.
            sma_short: Short-period SMA series.
            sma_long: Long-period SMA series.
            diff: Difference between short and long SMAs.

        Returns:
            Dictionary with signal data, or None if below confidence threshold.
        """
        price = ohlcv_data.loc[timestamp, "close"]
        sma_short_val = sma_short.loc[timestamp]
        sma_long_val = sma_long.loc[timestamp]
        diff_val = diff.loc[timestamp]

        # Calculate confidence based on crossover strength
        # Higher absolute difference indicates stronger signal
        confidence = self._calculate_confidence(diff_val, sma_long_val)

        if confidence < self.min_confidence:
            return None

        # Build metadata with strategy context
        metadata = {
            "sma_short": round(sma_short_val, 4),
            "sma_long": round(sma_long_val, 4),
            "difference": round(diff_val, 4),
            "difference_pct": round((diff_val / sma_long_val) * 100, 4),
            "short_window": self.short_window,
            "long_window": self.long_window,
        }

        return {
            "timestamp": timestamp,
            "signal_type": signal_type,
            "price": round(price, 4),
            "confidence": round(confidence, 4),
            "metadata": json.dumps(metadata),
        }

    def _calculate_confidence(self, diff: float, sma_long: float) -> float:
        """Calculate confidence score from crossover strength.

        Confidence is based on the percentage difference between the two SMAs.
        A larger gap indicates a stronger, more reliable crossover signal.

        Args:
            diff: Absolute difference between short and long SMAs.
            sma_long: Long-period SMA value (used for normalization).

        Returns:
            Confidence score between 0.0 and 1.0.
            Returns 0.0 if sma_long is zero to avoid division errors.
        """
        if sma_long == 0:
            return 0.0

        # Percentage difference between SMAs
        pct_diff = abs(diff / sma_long)

        # Normalize to 0-1 range using sigmoid-like scaling
        # 0.5% difference -> ~0.5 confidence
        # 1.0% difference -> ~0.76 confidence
        # 2.0% difference -> ~0.95 confidence
        confidence = min(1.0, pct_diff / 0.01)

        return confidence
