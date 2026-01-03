"""Time stepper for backtest execution intervals.

This module provides functionality to determine time step intervals for backtest
execution, supporting both fixed frequencies and auto-detection from data.
"""

import pandas as pd

from infrastructure.logging.logger import get_logger


class TimeStepper:
    """Determines time step intervals for backtest execution.

    This class generates DatetimeIndex intervals for backtest execution based on
    a specified frequency or auto-detection from data timestamps.

    Args:
        step_frequency: Frequency string ('daily', 'hourly', 'minute', 'auto', or pandas freq).
        start_date: Start date for backtest period.
        end_date: End date for backtest period.
        logger: Optional logger instance. If not provided, creates a new logger.
    """

    def __init__(
        self, step_frequency: str, start_date: pd.Timestamp, end_date: pd.Timestamp, logger=None
    ):
        """Initialize TimeStepper with frequency and date range.

        Args:
            step_frequency: Frequency string ('daily', 'hourly', 'minute', 'auto', or pandas freq).
            start_date: Start date for backtest period.
            end_date: End date for backtest period.
            logger: Optional logger instance. If not provided, creates a new logger.
        """
        self.step_frequency = step_frequency
        self.start_date = start_date
        self.end_date = end_date
        self.logger = logger or get_logger(self.__class__.__name__)

    def timedelta_to_freq(self, td: pd.Timedelta) -> str:
        """Convert Timedelta to pandas frequency string.

        Maps a Timedelta to the appropriate pandas frequency code based on duration.

        Args:
            td: Timedelta to convert.

        Returns:
            Pandas frequency string ('D' for days, 'H' for hours, 'T' for minutes, 'S' for seconds).
        """
        if td >= pd.Timedelta(days=1):
            return "D"
        elif td >= pd.Timedelta(hours=1):
            return "H"
        elif td >= pd.Timedelta(minutes=1):
            return "T"
        else:
            return "S"

    def determine_step_intervals(
        self, data_cache: dict[str, pd.DataFrame] | None = None
    ) -> pd.DatetimeIndex:
        """Determine time step intervals for backtest execution.

        Generates a DatetimeIndex of time steps based on the configured frequency.
        If frequency is 'auto', analyzes data timestamps to detect the most common interval.

        Args:
            data_cache: Optional dictionary mapping tickers to DataFrames for auto-detection.
                Required if step_frequency is 'auto'.

        Returns:
            DatetimeIndex containing time step intervals in UTC timezone.
        """
        if self.step_frequency == "auto":
            if not data_cache:
                return pd.DatetimeIndex([])

            all_timestamps = []
            for df in data_cache.values():
                all_timestamps.extend(df.index.tolist())

            if not all_timestamps:
                return pd.DatetimeIndex([])

            timestamps_series = pd.Series(all_timestamps).sort_values()
            diffs = timestamps_series.diff().dropna()
            most_common_diff = diffs.mode()[0] if not diffs.empty else pd.Timedelta(days=1)

            freq_str = self.timedelta_to_freq(most_common_diff)
            self.logger.info(f"Auto-detected step frequency: {freq_str}")

        elif self.step_frequency == "daily":
            freq_str = "D"
        elif self.step_frequency == "hourly":
            freq_str = "H"
        elif self.step_frequency == "minute":
            freq_str = "T"
        else:
            freq_str = self.step_frequency

        try:
            # Generate sequential time steps - backtest engine will iterate through these
            # one at a time, calling strategy.run_strategy() at each step
            intervals = pd.date_range(
                start=self.start_date, end=self.end_date, freq=freq_str, tz="UTC"
            )
            return intervals
        except Exception as e:
            self.logger.error(f"Invalid frequency '{freq_str}': {e}")
            return pd.date_range(start=self.start_date, end=self.end_date, freq="D", tz="UTC")
