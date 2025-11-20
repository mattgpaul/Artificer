# Trading Strategy Framework

## Overview

A trading strategy is a function that takes an OHLCV data window for a ticker and produces timestamped `buy` and `sell` signals. Strategies are executed sequentially at each time step during backtesting or forward testing, with each step seeing only historical data up to that point.

## Inputs and Outputs

### Inputs

- **`ohlcv_data`**: DataFrame indexed by datetime with required columns: `open`, `high`, `low`, `close`, `volume`
- **`ticker`**: Stock ticker symbol (string)
- **`lookback_bars`** (optional): Maximum number of historical bars to use per time step. If `None`, uses all available history up to the current time step.

### Outputs

Strategies implement two methods that return DataFrames:

- **`buy(ohlcv_data, ticker)`**: Returns DataFrame with buy signals
- **`sell(ohlcv_data, ticker)`**: Returns DataFrame with sell signals

Each DataFrame must have:
- **Index**: Timestamp (datetime)
- **Required columns**: `price` (float)
- **Optional columns**: `metadata` (JSON string)

The `BaseStrategy` class automatically:
- Combines buy and sell signals via `generate_signals()`
- Adds `signal_type` column ("buy" or "sell")
- Adds `side` column ("LONG" or "SHORT" based on `strategy_type`)
- Adds `ticker` and `signal_time` columns
- Optionally writes signals to InfluxDB

## Execution Workflow

The backtest engine executes strategies sequentially through time:

```mermaid
graph TD
    A[Backtest CLI] --> B[BacktestProcessor]
    B --> C[BacktestEngine]
    C --> D[TimeStepper]
    D --> E[SignalCollector]
    E --> F[BacktestStrategyWrapper]
    F --> G[strategy.run_strategy]
    G --> H[BaseStrategy.run_strategy]
    H --> I[query_ohlcv with lookback]
    I --> J[generate_signals]
    J --> K[buy/sell methods]
    K --> L[Combined signals]
    L --> M[ResultsGenerator]
    
    D -->|Sequential time steps| E
    F -->|Filters data to <= current_time| I
    I -->|Applies lookback_bars limit| J
```

### Key Points

1. **Sequential Execution**: `TimeStepper` generates a sequence of timestamps. The engine steps through each one sequentially.
2. **No Forward-Looking**: `BacktestStrategyWrapper` ensures strategies only see data with `index <= current_time`.
3. **Lookback Window**: If `lookback_bars` is set, the data is further truncated to the last N rows before being passed to the strategy.
4. **Signal Collection**: Signals are collected at each step and filtered to prevent duplicates.

## Strategy Types: LONG vs SHORT

Strategies declare their type via `strategy_type`:

- **`strategy_type = "LONG"`**: 
  - `buy()` = open/increase long exposure
  - `sell()` = close/reduce long exposure
- **`strategy_type = "SHORT"`**:
  - `buy()` = open/increase short exposure  
  - `sell()` = close/reduce short exposure

The base orchestration is identical for both types; the execution layer interprets `side` appropriately.

## Writing Your Own Strategy

### Step 1: Subclass BaseStrategy

```python
from system.algo_trader.strategy.base import BaseStrategy
import pandas as pd

class MyStrategy(BaseStrategy):
    strategy_type = "LONG"  # or "SHORT"
    
    def __init__(self, my_param: int, lookback_bars: int | None = None, ...):
        # Validate parameters
        if my_param < 1:
            raise ValueError("my_param must be >= 1")
        
        # Build strategy_args for InfluxDB tagging
        strategy_args = {"my_param": my_param}
        
        # Pass lookback_bars to base class
        super().__init__(strategy_args=strategy_args, lookback_bars=lookback_bars)
        
        self.my_param = my_param
        # Initialize any studies you need
        # self.my_study = SomeStudy(logger=self.logger)
    
    def _get_required_min_bars(self) -> int:
        # Return minimum bars needed for your calculations
        # This is validated against lookback_bars if set
        return self.my_param
```

### Step 2: Implement buy() and sell()

```python
def buy(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
    # Use studies to compute indicators
    # indicator = self.my_study.compute(ohlcv_data=ohlcv_data, ticker=ticker, ...)
    # if indicator is None:
    #     return pd.DataFrame()  # Insufficient data
    
    # Detect buy conditions
    buy_signals = []
    for idx in ohlcv_data.index:
        # Your buy logic here
        if some_condition:
            buy_signals.append({
                "timestamp": idx,
                "price": ohlcv_data.loc[idx, "close"],
                "metadata": json.dumps({"some_key": some_value})
            })
    
    if not buy_signals:
        return pd.DataFrame()
    
    signals_df = pd.DataFrame(buy_signals)
    signals_df = signals_df.set_index("timestamp")
    return signals_df

def sell(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
    # Similar pattern for sell signals
    ...
```

### Step 3: Implement add_strategy_arguments()

```python
def add_strategy_arguments(self, parser):
    parser.add_argument(
        "--my-param",
        type=int,
        default=10,
        help="My parameter description (default: 10)",
    )
```

### Example: SMACrossover

See `system/algo_trader/strategy/strategies/sma_crossover.py` for a complete working example:

- Uses `SimpleMovingAverage` study
- Implements `_get_required_min_bars()` based on window sizes
- Detects crossovers in `buy()` and `sell()`
- Returns signals with `price` and `metadata` (no confidence)

## Available Studies

The `studies` layer provides reusable technical indicators:

- **Moving Averages**: `SimpleMovingAverage` (see `strategy/utils/studies/moving_average/`)
- **Support/Resistance**: `FindValleys`, `FindPeaks` (see `strategy/utils/studies/support_resistance/`)

All studies inherit from `BaseStudy` and provide a `compute()` method that handles validation and returns Series or DataFrames.

## Lookback Window Validation

Strategies must implement `_get_required_min_bars()` to specify their minimum data requirements. If `lookback_bars` is set smaller than this minimum, the strategy will raise a `ValueError` with a clear error message.

Example:
- `SMACrossover` with `long_window=20` requires at least 20 bars
- If `lookback_bars=10` is set, validation fails immediately

This prevents strategies from running with insufficient data that would produce unreliable signals.

