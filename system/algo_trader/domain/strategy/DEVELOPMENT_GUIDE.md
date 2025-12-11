## Extending the Strategy Layer

This project is set up so that adding new behavior is as simple as:

1. Create a new `.py` file.
2. Add it to the appropriate `BUILD` target.
3. Reference it from YAML / CLI by name.

The discovery logic is registry-based and uses Python module scanning, so you *do not* need to touch the registries for new types.

---

## 1. Adding a New Strategy

**Goal**: Make a new trading strategy available to CLI / backtest.

### Steps

1. **Create the module**

   - Location: `system/algo_trader/strategy/strategies/`
   - Example: `my_strategy.py`

   Implement a `Strategy` subclass, e.g.:

  
   from system.algo_trader.strategy.strategy import Strategy

   class MyStrategy(Strategy):
       @staticmethod
       def add_arguments(parser) -> None:
           parser.add_argument("--window", type=int, default=20)

       def generate_signals(self, ohlcv_by_ticker, logger=None):
           ...
      The CLI name is derived from the class name:
   - `MyStrategy` → `my-strategy`
   - `SMACrossover` → `sma-crossover`

2. **Add the file to the BUILD**

   - Open `system/algo_trader/strategy/strategies/BUILD`
   - Add your file to `moving_average_lib.srcs` (or the appropriate `py_library`):

  
   py_library(
       name = "moving_average_lib",
       srcs = [
           "ema_crossover.py",
           "sma_crossover.py",
           "my_strategy.py",
       ],
       ...
   )
   3. **Use it**

   - CLI: `--strategy my-strategy`
   - YAML / params: use `my-strategy` as the strategy type.

`StrategyRegistry` will automatically scan the `strategies` package and register your class.

---

## 2. Adding a New Filter

**Goal**: Add a new filter type usable in filter YAML files.

### Key concepts

- Filters implement `evaluate(self, FilterContext) -> bool`.
- Each filter has:
  - A string `filter_type` used in YAML (`type:`).
  - Optional `from_config(params, logger)` to construct from YAML parameters.

### Steps

1. **Create the module**

   - Location: `system/algo_trader/strategy/filters/`
   - Example: `average_volume.py`

  
   from __future__ import annotations

   from typing import Any, ClassVar

   import pandas as pd

   from infrastructure.logging.logger import get_logger
   from system.algo_trader.strategy.filters.core import FilterContext
   from system.algo_trader.strategy.filters.base import BaseComparisonFilter  # or your own base

   class AverageVolumeFilter:
       filter_type: ClassVar[str] = "average_volume"

       def __init__(self, window: int, min_volume: float, logger=None) -> None:
           self.window = window
           self.min_volume = min_volume
           self.logger = logger or get_logger(self.__class__.__name__)

       def evaluate(self, context: FilterContext) -> bool:
           signal = context.signal
           ticker = signal.get("ticker")
           if not ticker:
               return False

           ohlcv = context.get_ticker_ohlcv(ticker)
           if ohlcv is None or ohlcv.empty or "volume" not in ohlcv.columns:
               return False

           if len(ohlcv) < self.window:
               return False

           recent = ohlcv["volume"].tail(self.window)
           avg_vol = float(recent.mean())
           return avg_vol >= self.min_volume

       @classmethod
       def from_config(
           cls, params: dict[str, Any], logger=None
       ) -> "AverageVolumeFilter" | None:
           window = params.get("window")
           min_volume = params.get("min_volume")
           if window is None or min_volume is None:
               if logger is not None:
                   logger.error("average_volume filter requires window and min_volume")
               return None
           try:
               return cls(window=int(window), min_volume=float(min_volume), logger=logger)
           except (TypeError, ValueError):
               if logger is not None:
                   logger.error("average_volume filter params must be numeric")
               return None
   2. **Add the file to the BUILD**

   - Open `system/algo_trader/strategy/filters/BUILD`
   - Add to `filters_lib.srcs`:

  
   py_library(
       name = "filters_lib",
       srcs = [
           "base.py",
           "config_loader.py",
           "core.py",
           "filters.py",
           "registry.py",
           "price_comparison.py",
           "sma_comparison.py",
           "average_volume.py",
       ],
       ...
   )
   3. **Use it in YAML**

   - Location: `system/algo_trader/strategy/filters/strategies/*.yaml`

  
   filters:
     - type: average_volume
       params:
         window: 20
         min_volume: 1000000
   `FilterRegistry` scans all modules under `strategy.filters` and registers any class with `filter_type`. `config_loader` creates instances via `from_config` or `__init__(**params, logger=...)`.

---

## 3. Adding a New Position Manager Rule

**Goal**: Add a new rule usable in position manager strategy YAMLs.

### Key concepts

- Rules implement `evaluate(self, PositionRuleContext) -> PositionDecision`.
- Each rule has:
  - `rule_type` string used as the YAML key inside `rules:`.
  - Optional `from_config(params, logger)` to construct from YAML.

### Steps

1. **Create the rule module**

   - Location: `system/algo_trader/strategy/position_manager/rules/`
   - Example: `my_position_rule.py`

  
   from __future__ import annotations

   from typing import Any, ClassVar

   from infrastructure.logging.logger import get_logger
   from system.algo_trader.strategy.position_manager.rules.base import (
       PositionDecision,
       PositionRuleContext,
   )

   class MyPositionRule:
       rule_type: ClassVar[str] = "my_position_rule"

       def __init__(self, threshold: float, logger=None) -> None:
           self.threshold = threshold
           self.logger = logger or get_logger(self.__class__.__name__)

       def evaluate(self, context: PositionRuleContext) -> PositionDecision:
           # Decide allow_entry / exit_fraction based on context
           ...
           return PositionDecision()

       @classmethod
       def from_config(
           cls, params: dict[str, Any], logger=None
       ) -> "MyPositionRule" | None:
           threshold = params.get("threshold")
           if threshold is None:
               if logger is not None:
                   logger.error("my_position_rule requires threshold")
               return None
           try:
               return cls(threshold=float(threshold), logger=logger)
           except (TypeError, ValueError):
               if logger is not None:
                   logger.error("my_position_rule threshold must be numeric")
               return None
   2. **Add to BUILD**

   - `system/algo_trader/strategy/position_manager/BUILD`:

  
   py_library(
       name = "position_manager_lib",
       srcs = [
           "config_loader.py",
           "position_manager.py",
           "rules/base.py",
           "rules/pipeline.py",
           "rules/registry.py",
           "rules/scaling.py",
           "rules/stop_loss.py",
           "rules/take_profit.py",
           "rules/my_position_rule.py",
       ],
       ...
   )
   3. **Use in YAML**

  
   rules:
     - my_position_rule:
         threshold: 0.05
   The loader still has built-ins (`scaling`, `take_profit`, `stop_loss`), and for any other key it asks the registry for a rule with that `rule_type`.

---

## 4. Adding a New Portfolio Manager Rule

**Goal**: Add a portfolio-level rule to control capital allocation.

### Key concepts

- Rules implement `evaluate(self, PortfolioRuleContext) -> PortfolioDecision`.
- Each rule has:
  - `rule_type` string (YAML key).
  - Optional `from_config(params, logger)`.

### Steps

1. **Create rule module**

   - Location: `system/algo_trader/strategy/portfolio_manager/rules/`
   - Example: `max_positions_per_ticker.py`

  
   from __future__ import annotations

   from typing import Any, ClassVar

   from infrastructure.logging.logger import get_logger
   from system.algo_trader.strategy.portfolio_manager.rules.base import (
       PortfolioDecision,
       PortfolioRuleContext,
   )

   class MaxPositionsPerTickerRule:
       rule_type: ClassVar[str] = "max_positions_per_ticker"

       def __init__(self, max_positions: int, logger=None) -> None:
           self.max_positions = max_positions
           self.logger = logger or get_logger(self.__class__.__name__)

       def evaluate(self, context: PortfolioRuleContext) -> PortfolioDecision:
           # Inspect portfolio_state / signal to decide
           ...
           return PortfolioDecision(allow_entry=True)

       @classmethod
       def from_config(
           cls, params: dict[str, Any], logger=None
       ) -> "MaxPositionsPerTickerRule" | None:
           max_positions = params.get("max_positions")
           if max_positions is None:
               if logger is not None:
                   logger.error("max_positions_per_ticker requires max_positions")
               return None
           try:
               return cls(max_positions=int(max_positions), logger=logger)
           except (TypeError, ValueError):
               if logger is not None:
                   logger.error("max_positions_per_ticker max_positions must be int")
               return None
   2. **Add to BUILD**

   - `system/algo_trader/strategy/portfolio_manager/BUILD`:

  
   py_library(
       name = "portfolio_manager_lib",
       srcs = [
           "config_loader.py",
           "portfolio_manager.py",
           "rules/base.py",
           "rules/fractional_position_size.py",
           "rules/registry.py",
           "rules/max_capital_deployed.py",
           "rules/max_positions_per_ticker.py",
       ],
       ...
   )
   3. **Use in YAML**

  
   rules:
     - max_positions_per_ticker:
         max_positions: 10
   The loader has explicit support for `max_capital_deployed` and `fractional_position_size`; any other key is resolved via the registry by `rule_type`.

---

## 5. Summary: Common Pattern

For **any new extension point** (strategy, filter, position rule, portfolio rule):

1. **Create a module** in the relevant package.
2. **Provide a type identifier**:
   - `Strategy`: class name → CLI name via `StrategyRegistry`.
   - Filter: `filter_type`.
   - Position rule: `rule_type`.
   - Portfolio rule: `rule_type`.
3. **Optionally implement `from_config(params, logger)`** when YAML → constructor mapping is non-trivial.
4. **Add the module to the correct `py_library.srcs` in BUILD**.
5. **Reference it in YAML / CLI** using the appropriate name.

No registry files need to be touched for new types; they discover your classes automatically based on these conventions.