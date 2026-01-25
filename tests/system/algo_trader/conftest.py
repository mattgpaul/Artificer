"""Shared fixtures for algo_trader tests.

All common fixtures, mocks, and test data are defined here
to reduce code duplication across test files.
"""

from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import pytest

from algo_trader.domain.models import (
    Account,
    Event,
    HistoricalOHLCV,
    JournalError,
    JournalInput,
    JournalOutput,
    MarketOrder,
    Orders,
    Position,
    Positions,
    PortfolioManager,
    Quote,
)
from algo_trader.domain.ports.account_port import AccountPort
from algo_trader.domain.ports.controller_port import ControllerPort
from algo_trader.domain.ports.event_port import EventPort
from algo_trader.domain.ports.historical_port import HistoricalPort
from algo_trader.domain.ports.journal_port import JournalPort
from algo_trader.domain.ports.order_port import OrderPort
from algo_trader.domain.ports.portfolio_manager_port import PortfolioManagerPort
from algo_trader.domain.ports.quote_port import QuotePort
from algo_trader.domain.ports.strategy_port import StrategyPort
from algo_trader.domain.states import (
    ControllerCommand,
    EngineState,
    EventType,
    OrderDuration,
    OrderInstruction,
    OrderTaxLotMethod,
    OrderType,
    TradingState,
    TickReason,
)


# Fake adapter implementations
class FakeHistoricalPort(HistoricalPort):
    """Simple fake historical data port."""

    def __init__(self, data: Optional[HistoricalOHLCV] = None):
        self.data = data or HistoricalOHLCV(
            period="1Y",
            frequency="1D",
            start=datetime.now(timezone.utc),
            end=datetime.now(timezone.utc),
            data={"AAPL": pd.DataFrame({"close": [100.0, 101.0, 102.0]})},
        )

    def get_data(self) -> HistoricalOHLCV:
        return self.data


class FakeQuotePort(QuotePort):
    """Simple fake quote port."""

    def __init__(self, quote: Optional[Quote] = None):
        self.quote = quote or Quote(
            timestamp=datetime.now(timezone.utc),
            asset_class="EQUITY",
            bid={"AAPL": 100.0},
            ask={"AAPL": 100.5},
            bid_size={"AAPL": 100.0},
            ask_size={"AAPL": 100.0},
            last={"AAPL": 100.25},
            volume={"AAPL": 1000000.0},
            change={"AAPL": 0.5},
            change_pct={"AAPL": 0.5},
        )

    def get_quotes(self) -> Quote:
        return self.quote


class FakeAccountPort(AccountPort):
    """Simple fake account port."""

    def __init__(
        self,
        account: Optional[Account] = None,
        positions: Optional[Positions] = None,
    ):
        self.account = account or Account(
            timestamp=datetime.now(timezone.utc),
            cash=100000.0,
            buying_power=100000.0,
            position_value=0.0,
            net_liquidation=100000.0,
            commission_and_fees=0.0,
        )
        self.positions = positions or Positions(
            timestamp=datetime.now(timezone.utc),
            positions=[],
        )

    def get_account(self) -> Account:
        return self.account

    def get_positions(self) -> Positions:
        return self.positions


class FakeOrderPort(OrderPort):
    """Simple fake order port."""

    def __init__(self):
        self.sent_orders: list[Orders] = []
        self.open_orders = Orders(timestamp=datetime.now(timezone.utc), orders=[])

    def send_orders(self, orders: Orders) -> Orders:
        self.sent_orders.append(orders)
        return orders

    def get_open_orders(self) -> Orders:
        return self.open_orders

    def cancel_order(self, order_id: str) -> bool:
        return True

    def cancel_all_orders(self) -> bool:
        return True

    def get_all_orders(self) -> Orders:
        return Orders(timestamp=datetime.now(timezone.utc), orders=[])


class FakeStrategyPort(StrategyPort):
    """Simple fake strategy port."""

    def __init__(self, signals: Optional[Orders] = None):
        self.signals = signals or Orders(
            timestamp=datetime.now(timezone.utc),
            orders=[],
        )

    def get_signals(
        self,
        historical_data: HistoricalOHLCV,
        quote_data: Quote,
        position_data: Positions,
    ) -> Orders:
        return self.signals


class FakePortfolioManagerPort(PortfolioManagerPort):
    """Simple fake portfolio manager port."""

    def __init__(self, state: Optional[PortfolioManager] = None):
        self.state = state or PortfolioManager(
            timestamp=datetime.now(timezone.utc),
            trading_state=TradingState.NEUTRAL,
            max_exposure_pct=100.0,
            max_position_pct=10.0,
        )
        self.handle_signals_calls: list[tuple] = []

    def get_state(self) -> PortfolioManager:
        return self.state

    def handle_signals(
        self,
        signals: Orders,
        quote_data: Quote,
        account_data: Account,
        position_data: Positions,
        open_orders: Orders,
        portfolio_state: PortfolioManager,
    ) -> Orders:
        self.handle_signals_calls.append(
            (signals, quote_data, account_data, position_data, open_orders, portfolio_state)
        )
        # Return signals as orders (simple passthrough)
        return signals


class FakeJournalPort(JournalPort):
    """Simple fake journal port."""

    def __init__(self):
        self.inputs: list[JournalInput] = []
        self.outputs: list[JournalOutput] = []
        self.errors: list[JournalError] = []

    def report_input(self, input: JournalInput) -> None:
        self.inputs.append(input)

    def report_output(self, output: JournalOutput) -> None:
        self.outputs.append(output)

    def report_error(self, error: JournalError) -> None:
        self.errors.append(error)


class FakeControllerPort(ControllerPort):
    """Simple fake controller port."""

    def __init__(self):
        self.published_statuses: list[EngineState] = []

    def wait_for_command(self, timeout_s: Optional[float]) -> Optional[ControllerCommand]:
        return None

    def publish_status(self, status: EngineState) -> None:
        self.published_statuses.append(status)


class FakeEventPort(EventPort):
    """Simple fake event port that returns scripted events."""

    def __init__(self, events: Optional[list[Event]] = None):
        self.events = events or []
        self.index = 0

    def wait_for_event(self, timeout_s: Optional[float]) -> Optional[Event]:
        if self.index >= len(self.events):
            return None
        event = self.events[self.index]
        self.index += 1
        return event


# Fixtures
@pytest.fixture
def fake_historical_port():
    """Provide a fake historical port."""
    return FakeHistoricalPort()


@pytest.fixture
def fake_quote_port():
    """Provide a fake quote port."""
    return FakeQuotePort()


@pytest.fixture
def fake_account_port():
    """Provide a fake account port."""
    return FakeAccountPort()


@pytest.fixture
def fake_order_port():
    """Provide a fake order port."""
    return FakeOrderPort()


@pytest.fixture
def fake_strategy_port():
    """Provide a fake strategy port."""
    return FakeStrategyPort()


@pytest.fixture
def fake_portfolio_manager_port():
    """Provide a fake portfolio manager port."""
    return FakePortfolioManagerPort()


@pytest.fixture
def fake_journal_port():
    """Provide a fake journal port."""
    return FakeJournalPort()


@pytest.fixture
def fake_controller_port():
    """Provide a fake controller port."""
    return FakeControllerPort()


@pytest.fixture
def fake_event_port():
    """Provide a fake event port."""
    return FakeEventPort()


@pytest.fixture
def engine_with_fakes(
    fake_historical_port,
    fake_quote_port,
    fake_account_port,
    fake_order_port,
    fake_strategy_port,
    fake_portfolio_manager_port,
    fake_journal_port,
    fake_controller_port,
    fake_event_port,
):
    """Provide an Engine instance with all fake ports."""
    from algo_trader.domain.engine import Engine

    return Engine(
        historical_port=fake_historical_port,
        quote_port=fake_quote_port,
        account_port=fake_account_port,
        order_port=fake_order_port,
        strategy_port=fake_strategy_port,
        portfolio_manager_port=fake_portfolio_manager_port,
        journal_port=fake_journal_port,
        controller_port=fake_controller_port,
        event_port=fake_event_port,
    )


# Test data factories
@pytest.fixture
def sample_market_order():
    """Factory for creating sample market orders."""
    from uuid import uuid4

    def _create(
        symbol: str = "AAPL",
        quantity: int = 10,
        instruction: OrderInstruction = OrderInstruction.BUY_TO_OPEN,
    ):
        return MarketOrder(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            symbol=symbol,
            quantity=quantity,
            order_type=OrderType.MARKET,
            order_instruction=instruction,
            order_duration=OrderDuration.DAY,
            order_tax_lot_method=OrderTaxLotMethod.FIFO,
        )

    return _create


@pytest.fixture
def sample_position():
    """Factory for creating sample positions."""

    def _create(symbol: str = "AAPL", quantity: int = 10):
        return Position(
            timestamp=datetime.now(timezone.utc),
            symbol=symbol,
            quantity=quantity,
            cost_basis=100.0,
            current_price=101.0,
            pnl_open=10.0,
            net_liquidation=1010.0,
        )

    return _create
