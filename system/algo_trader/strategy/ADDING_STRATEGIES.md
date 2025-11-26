# Adding New Trading Strategies

This document explains how to add new trading strategies to the Artificer backtesting system. With the new strategy registry system, adding strategies is now streamlined and requires minimal manual configuration.

## Overview

The strategy registry automatically discovers and registers all `Strategy` subclasses, eliminating the need for manual registration in multiple places. When you add a new strategy, it will automatically appear in the CLI.

## Steps to Add a New Strategy

### 1. Create Your Strategy Class

Create a new Python file in `system/algo_trader/strategy/strategies/` that implements your strategy:

```python
from system.algo_trader.strategy.strategy import Side, Strategy
import pandas as pd

class MyNewStrategy(Strategy):
    def __init__(
        self,
        my_param: int = 10,
        side: Side = Side.LONG,
        window: int | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(side=side, window=window, **extra)
        self.my_param = my_param
    
    @classmethod
    def add_arguments(cls, parser) -> None:
        """Add strategy-specific CLI arguments."""
        Strategy.add_arguments(parser)
        parser.add_argument(
            "--my-param",
            type=int,
            default=10,
            help="My parameter (default: 10)",
        )
    
    def buy(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        # Your buy signal logic
        return pd.DataFrame()
    
    def sell(self, ohlcv_data: pd.DataFrame, ticker: str) -> pd.DataFrame:
        # Your sell signal logic
        return pd.DataFrame()
```

### 2. Add to BUILD File

Add your strategy file to `system/algo_trader/strategy/BUILD` in the `strategies` library:

```python
py_library(
    name = "strategies",
    srcs = [
        # ... existing files ...
        "strategies/my_new_strategy.py",  # Add this line
    ],
    # ... rest of config ...
)
```

### 3. Register in Strategy Registry

Add your strategy module to the registry's discovery list in `system/algo_trader/strategy/strategy_registry.py`:

```python
strategy_module_names = [
    "system.algo_trader.strategy.strategies.sma_crossover",
    "system.algo_trader.strategy.strategies.ema_crossover",
    "system.algo_trader.strategy.strategies.my_new_strategy",  # Add this line
]
```

### 4. That's It!

Your strategy is now automatically:
- ✅ Discovered by the registry
- ✅ Available in the CLI (as `my-new-strategy`)
- ✅ Registered with argument parsing
- ✅ Available for backtesting

## How It Works

### Strategy Registry

The `StrategyRegistry` class (`strategy_registry.py`) automatically:

1. **Discovers strategies**: Imports all strategy modules and finds `Strategy` subclasses
2. **Maps class names to CLI names**: Converts `MyNewStrategy` → `my-new-strategy`
3. **Registers CLI arguments**: Automatically calls each strategy's `add_arguments()` method
4. **Creates instances**: Uses introspection to extract parameters from CLI args

### CLI Name Conversion

Class names are automatically converted to CLI-friendly names:
- `SMACrossover` → `sma-crossover`
- `EMACrossover` → `ema-crossover`
- `MyNewStrategy` → `my-new-strategy`
- `RSIStrategy` → `rsi-strategy`

The conversion handles acronyms correctly (SMA, EMA, RSI, etc.).

## Usage Example

Once registered, your strategy can be used directly:

```bash
bazel run //system/algo_trader/backtest:main -- \
  --tickers AAPL MSFT \
  --start-date 2020-01-01 \
  --end-date 2021-01-01 \
  --account-value 100000 \
  my-new-strategy \
  --my-param 20
```

## Backward Compatibility

The registry supports both:
- **CLI names**: `sma-crossover`, `ema-crossover` (preferred)
- **Class names**: `SMACrossover`, `EMACrossover` (for backward compatibility)

## Benefits

1. **Less boilerplate**: No need to modify `main.py` or `worker.py`
2. **Automatic discovery**: Strategies are found automatically
3. **Type safety**: Uses introspection to validate parameters
4. **Consistent naming**: Automatic CLI name conversion
5. **Single source of truth**: BUILD file lists all strategies

## Troubleshooting

### Strategy Not Appearing in CLI

1. Check that your strategy file is in `system/algo_trader/strategy/BUILD`
2. Verify the module is imported in `strategy_registry.py`
3. Ensure your class inherits from `Strategy`
4. Check that `add_arguments()` is implemented

### Parameter Not Being Passed

1. Verify the parameter name matches between `add_arguments()` and `__init__()`
2. Check that the parameter is not filtered out in `create_strategy()`
3. Use `--help` to see all available arguments for your strategy

### Import Errors

1. Ensure all dependencies are listed in the BUILD file
2. Check that the strategy module can be imported independently
3. Verify there are no circular imports

## Future Improvements

Potential enhancements to the registry system:

1. **Automatic module discovery**: Use `pkgutil` to find all modules automatically
2. **Strategy metadata**: Add descriptions, tags, or categories
3. **Validation**: Automatic parameter validation based on type hints
4. **Documentation generation**: Auto-generate strategy docs from docstrings

