"""Unit tests for Engine pause and cooldown logic.

Tests cover:
- Manual pause/resume behavior
- Cooldown pause via pause_until
- is_paused() logic combining both pause types
- Portfolio-managed pause_until integration

All external dependencies are mocked via conftest.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from system.algo_trader.domain.engine import Engine
from system.algo_trader.domain.events import MarketEvent, OverrideEvent
from system.algo_trader.domain.models import Quote
from system.algo_trader.ports.portfolio import PortfolioDecision


class TestEnginePauseLogic:
    """Test Engine pause and cooldown functionality."""

    def test_is_paused_returns_false_when_not_paused(self, engine: Engine):
        """Test is_paused returns False when engine is not paused."""
        assert engine.is_paused() is False

    def test_is_paused_returns_true_when_manually_paused(self, engine: Engine):
        """Test is_paused returns True when manually paused."""
        engine.paused = True
        assert engine.is_paused() is True

    def test_is_paused_returns_true_when_cooldown_active(self, engine: Engine, mock_clock):
        """Test is_paused returns True when pause_until is in future."""
        future_time = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        engine.pause_until = future_time
        mock_clock.now.return_value = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
        assert engine.is_paused() is True

    def test_is_paused_returns_false_when_cooldown_expired(self, engine: Engine, mock_clock):
        """Test is_paused returns False when pause_until is in past."""
        past_time = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
        engine.pause_until = past_time
        mock_clock.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert engine.is_paused() is False

    def test_on_override_pause_sets_paused_flag(self, engine: Engine):
        """Test pause override sets paused flag."""
        event = OverrideEvent(
            ts=datetime.now(tz=timezone.utc),
            command="pause",
            args={},
        )
        engine.on_override(event)
        assert engine.paused is True

    def test_on_override_resume_clears_paused_and_cooldown(self, engine: Engine):
        """Test resume override clears both paused flag and pause_until."""
        engine.paused = True
        engine.pause_until = datetime.now(tz=timezone.utc) + timedelta(seconds=300)
        event = OverrideEvent(
            ts=datetime.now(tz=timezone.utc),
            command="resume",
            args={},
        )
        engine.on_override(event)
        assert engine.paused is False
        assert engine.pause_until is None

    def test_on_market_skips_strategy_when_paused(self, engine: Engine, mock_strategy):
        """Test on_market skips strategy when engine is paused."""
        engine.paused = True
        event = MarketEvent(
            kind="quote",
            payload=Quote(symbol="AAPL", ts=datetime.now(tz=timezone.utc), price=100),
        )
        engine.on_market(event)
        mock_strategy.on_market.assert_not_called()

    def test_on_market_updates_pause_until_from_portfolio(self, engine: Engine, mock_portfolio):
        """Test on_market updates pause_until when portfolio returns pause_until."""
        future_time = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        mock_portfolio.manage.return_value = PortfolioDecision(
            proposed_intents=(),
            final_intents=(),
            pause_until=future_time,
            audit=None,
        )
        event = MarketEvent(
            kind="quote",
            payload=Quote(symbol="AAPL", ts=datetime.now(tz=timezone.utc), price=100),
        )
        engine.on_market(event)
        assert engine.pause_until == future_time

    def test_on_market_extends_pause_until_when_portfolio_requests_longer(
        self,
        engine: Engine,
        mock_portfolio,
    ):
        """Test on_market extends pause_until when portfolio requests longer cooldown."""
        existing_time = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
        engine.pause_until = existing_time
        longer_time = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        mock_portfolio.manage.return_value = PortfolioDecision(
            proposed_intents=(),
            final_intents=(),
            pause_until=longer_time,
            audit=None,
        )
        event = MarketEvent(
            kind="quote",
            payload=Quote(symbol="AAPL", ts=datetime.now(tz=timezone.utc), price=100),
        )
        engine.on_market(event)
        assert engine.pause_until == longer_time

