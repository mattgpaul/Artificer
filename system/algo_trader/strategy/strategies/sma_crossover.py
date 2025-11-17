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
from system.algo_trader.strategy.utils.studies.moving_average.simple_moving_average import (
    SimpleMovingAverage,
)


class SMACrossoverStrategy(BaseStrategy):
    """SMA crossover strategy for generating buy/sell trading signals.

    This strategy detects crossover points between two simple moving averages:
    - Buy signal: Short-period SMA crosses above long-period SMA (bullish)
    - Sell signal: Short-period SMA crosses below long-period SMA (bearish)

    Attributes:
        short_window: Number of periods for the short-term SMA (default: 10).
        long_window: Number of periods for the long-term SMA (default: 20).
    """

    strategy_type = "LONG"

    def __init__(
        self,
        short_window: int = 10,
        long_window: int = 20,
        min_confidence: float = 0.0,
        database: str = "algo-trader-database",
        write_config: BatchWriteConfig | None = None,
        use_threading: bool = False,
        config: Any = None,
        thread_config: Any = None,
    ):
        """Initialize SMA crossover strategy.

        Args:
            short_window: Period for short-term SMA (must be less than long_window).
            long_window: Period for long-term SMA (must be greater than short_window).
            min_confidence: Minimum confidence threshold (0.0 to 1.0) for filtering signals.
            database: InfluxDB database name for signal persistence.
            write_config: Optional batch write configuration for InfluxDB.
            use_threading: Enable parallel processing for multiple tickers.
            config: Optional InfluxDB configuration override.
            thread_config: Optional ThreadConfig for thread management.

        Raises:
            ValueError: If short_window >= long_window or parameters are invalid.
        """
        if short_window >= long_window:
            raise ValueError(
                f"short_window ({short_window}) must be less than long_window ({long_window})"
            )
        if short_window < 2:
            raise ValueError(f"short_window must be at least 2, got {short_window}")
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError(f"min_confidence must be in [0.0, 1.0], got {min_confidence}")

        strategy_name = f"sma_crossover_{short_window}_{long_window}"

        # Use default write_config from base class if not provided
        init_kwargs = {
            "strategy_name": strategy_name,
            "database": database,
            "use_threading": use_threading,
            "config": config,
            "thread_config": thread_config,
        }
        if write_config is not None:
            init_kwargs["write_config"] = write_config

        super().__init__(**init_kwargs)

        self.short_window = short_window
        self.long_window = long_window
        self.min_confidence = min_confidence

        # Initialize SMA study instances for calculations
        self.sma_study = SimpleMovingAverage(logger=self.logger)

        self.logger.debug(
            f"SMA Crossover initialized: short={short_window}, long={long_window}, "
            f"min_confidence={min_confidence}"
        )

    def buy(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Generate buy signals from OHLCV data.

        Detects bullish crossovers where the short-period SMA crosses above
        the long-period SMA, indicating a potential upward trend.

        Args:
            ohlcv_data: DataFrame with OHLCV data indexed by datetime.
            ticker: Stock ticker symbol (for logging purposes).

        Returns:
            DataFrame with buy signals indexed by timestamp. Contains columns:
            timestamp, price, confidence, metadata. Empty DataFrame if no
            buy signals detected.

        Example:
            >>> buy_signals = strategy.buy(ohlcv_data, 'AAPL')
            >>> assert 'price' in buy_signals.columns
        """
        sma_short, sma_long, current_diff = self._calculate_smas(ohlcv_data, ticker)
        if sma_short is None:
            return pd.DataFrame()

        # Detect bullish crossovers: short crosses above long
        previous_diff = (sma_short - sma_long).shift(1)
        bullish_crossover = (previous_diff < 0) & (current_diff > 0)

        # Extract buy signals
        buy_signals = []
        for idx in ohlcv_data.index:
            if bullish_crossover.loc[idx]:
                signal = self._create_signal(idx, ohlcv_data, sma_short, sma_long, current_diff)
                buy_signals.append(signal)

        if not buy_signals:
            self.logger.debug(f"No buy signals detected for {ticker}")
            return pd.DataFrame()

        # Convert to DataFrame with datetime index
        signals_df = pd.DataFrame(buy_signals)
        signals_df = signals_df.set_index("timestamp")
        signals_df.index.name = None

        self.logger.debug(f"Generated {len(signals_df)} buy signals for {ticker}")
        return signals_df

    def sell(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Generate sell signals from OHLCV data.

        Detects bearish crossovers where the short-period SMA crosses below
        the long-period SMA, indicating a potential downward trend.

        Args:
            ohlcv_data: DataFrame with OHLCV data indexed by datetime.
            ticker: Stock ticker symbol (for logging purposes).

        Returns:
            DataFrame with sell signals indexed by timestamp. Contains columns:
            timestamp, price, confidence, metadata. Empty DataFrame if no
            sell signals detected.

        Example:
            >>> sell_signals = strategy.sell(ohlcv_data, 'AAPL')
            >>> assert 'price' in sell_signals.columns
        """
        sma_short, sma_long, current_diff = self._calculate_smas(ohlcv_data, ticker)
        if sma_short is None:
            return pd.DataFrame()

        # Detect bearish crossovers: short crosses below long
        previous_diff = (sma_short - sma_long).shift(1)
        bearish_crossover = (previous_diff > 0) & (current_diff < 0)

        # Extract sell signals
        sell_signals = []
        for idx in ohlcv_data.index:
            if bearish_crossover.loc[idx]:
                signal = self._create_signal(idx, ohlcv_data, sma_short, sma_long, current_diff)
                sell_signals.append(signal)

        if not sell_signals:
            self.logger.debug(f"No sell signals detected for {ticker}")
            return pd.DataFrame()

        # Convert to DataFrame with datetime index
        signals_df = pd.DataFrame(sell_signals)
        signals_df = signals_df.set_index("timestamp")
        signals_df.index.name = None

        self.logger.debug(f"Generated {len(signals_df)} sell signals for {ticker}")
        return signals_df

    def generate_signals(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Generate buy and sell signals from OHLCV data.

        Args:
            ohlcv_data: DataFrame with OHLCV data indexed by datetime.
            ticker: Stock ticker symbol.

        Returns:
            DataFrame with columns: signal_type, price, confidence, metadata.
            Empty DataFrame if no signals generated or data is invalid.
        """
        if ohlcv_data is None or ohlcv_data.empty:
            return pd.DataFrame()

        # Get buy and sell signals
        buy_signals = self.buy(ohlcv_data, ticker)
        sell_signals = self.sell(ohlcv_data, ticker)

        # Combine signals
        all_signals = []
        if not buy_signals.empty:
            buy_signals["signal_type"] = "buy"
            all_signals.append(buy_signals)
        if not sell_signals.empty:
            sell_signals["signal_type"] = "sell"
            all_signals.append(sell_signals)

        if not all_signals:
            return pd.DataFrame()

        # Combine and sort by timestamp
        combined = pd.concat(all_signals).sort_index()

        # Filter by min_confidence if set
        if self.min_confidence > 0.0 and "confidence" in combined.columns:
            combined = combined[combined["confidence"] >= self.min_confidence]

        return combined

    def _calculate_confidence(self, diff: float, sma_long: float) -> float:
        """Calculate confidence score based on SMA difference.

        Confidence is calculated as the absolute percentage difference between
        short and long SMAs, capped at 1.0. Higher differences indicate stronger
        signals.

        Args:
            diff: Difference between short and long SMA (short - long).
            sma_long: Long-period SMA value.

        Returns:
            Confidence score between 0.0 and 1.0. Returns 0.0 if sma_long is zero.
        """
        if sma_long == 0.0:
            return 0.0

        # Calculate absolute percentage difference
        abs_pct_diff = abs(diff / sma_long) * 100

        # Convert to confidence (capped at 1.0)
        # Using a sigmoid-like function: confidence = min(1.0, abs_pct_diff / 2.0)
        # This means 2% difference = 1.0 confidence, scales linearly below that
        confidence = min(1.0, abs_pct_diff / 2.0)

        return round(confidence, 4)

    def add_strategy_arguments(self, parser):
        """Add SMA crossover-specific arguments to argument parser.

        Adds --short and --long arguments for configuring SMA window periods.

        Args:
            parser: argparse.ArgumentParser instance to add arguments to.

        Example:
            >>> parser = argparse.ArgumentParser()
            >>> strategy.add_strategy_arguments(parser)
            >>> args = parser.parse_args(['--short', '5', '--long', '15'])
        """
        parser.add_argument(
            "--short",
            type=int,
            default=10,
            help="Short-term SMA window period (default: 10)",
        )
        parser.add_argument(
            "--long",
            type=int,
            default=20,
            help="Long-term SMA window period (default: 20)",
        )

    def _calculate_smas(
        self, ohlcv_data: pd.DataFrame, ticker: str
    ) -> tuple[pd.Series, pd.Series, pd.Series] | tuple[None, None, None]:
        """Calculate short and long simple moving averages from OHLCV data.

        Uses SimpleMovingAverage study instances to perform calculations with
        validation. Returns None values if validation fails.

        Args:
            ohlcv_data: DataFrame with OHLCV data indexed by datetime.
                Must contain 'close' column.
            ticker: Stock ticker symbol (for logging purposes).

        Returns:
            Tuple of (sma_short, sma_long, current_diff) where:
            - sma_short: Series of short-period SMA values
            - sma_long: Series of long-period SMA values
            - current_diff: Series of differences (sma_short - sma_long)

            Returns (None, None, None) if data is invalid or insufficient.

        Example:
            >>> sma_short, sma_long, diff = strategy._calculate_smas(ohlcv_data, 'AAPL')
            >>> assert len(sma_short) == len(ohlcv_data)
        """
        # Calculate short-period SMA using study
        sma_short = self.sma_study.compute(
            ohlcv_data=ohlcv_data, window=self.short_window, ticker=ticker, column="close"
        )
        if sma_short is None:
            return None, None, None

        # Calculate long-period SMA using study
        sma_long = self.sma_study.compute(
            ohlcv_data=ohlcv_data, window=self.long_window, ticker=ticker, column="close"
        )
        if sma_long is None:
            return None, None, None

        # Calculate difference between SMAs
        current_diff = sma_short - sma_long

        return sma_short, sma_long, current_diff

    def _create_signal(
        self,
        timestamp: pd.Timestamp,
        ohlcv_data: pd.DataFrame,
        sma_short: pd.Series,
        sma_long: pd.Series,
        diff: pd.Series,
    ) -> dict[str, Any]:
        """Create a signal dictionary with metadata.

        Args:
            timestamp: Datetime of the crossover event.
            ohlcv_data: Original OHLCV DataFrame.
            sma_short: Short-period SMA series.
            sma_long: Long-period SMA series.
            diff: Difference between short and long SMAs.

        Returns:
            Dictionary with signal data including confidence.
        """
        price = ohlcv_data.loc[timestamp, "close"]
        sma_short_val = sma_short.loc[timestamp]
        sma_long_val = sma_long.loc[timestamp]
        diff_val = diff.loc[timestamp]

        # Calculate confidence
        confidence = self._calculate_confidence(diff_val, sma_long_val)

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
            "price": round(price, 4),
            "confidence": confidence,
            "metadata": json.dumps(metadata),
        }
