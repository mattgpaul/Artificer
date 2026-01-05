"""Unit tests for SimplePortfolio risk controls.

Tests cover:
- Max drawdown flatten + pause behavior
- Max position size resizing
- Max gross exposure resizing
- Disabled symbols filtering
- Max symbols gate
- Slippage violation detection
- Cooldown after loss

All external dependencies are mocked via conftest.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from system.algo_trader.domain.events import MarketEvent
from system.algo_trader.domain.models import Fill, OrderIntent, Quote, Side
from system.algo_trader.domain.portfolio import SimplePortfolio


class TestPortfolioRiskControls:
    """Test portfolio risk control mechanisms."""

    def test_manage_max_drawdown_triggers_flatten(self):
        """Test max drawdown triggers flatten intents for all positions."""
        portfolio = SimplePortfolio(
            max_drawdown=Decimal("0.10"),
            cooldown_after_drawdown_seconds=300,
        )
        portfolio.equity.cash = Decimal("80000")
        portfolio.equity.positions_by_symbol["AAPL"] = Decimal("100")
        portfolio.equity.positions_by_symbol["NVDA"] = Decimal("50")
        portfolio.equity.update_price("AAPL", Decimal("100"))
        portfolio.equity.update_price("NVDA", Decimal("200"))
        portfolio.equity.peak_equity = Decimal("100000")
        portfolio.equity.refresh()  # Drawdown = (100k - 100k) / 100k = 0, but equity is 100k

        # Force drawdown by dropping prices
        portfolio.equity.update_price("AAPL", Decimal("50"))
        portfolio.equity.update_price("NVDA", Decimal("100"))
        # Equity = 80k + 5k + 5k = 90k, drawdown = (100k - 90k) / 100k = 0.10

        event = MarketEvent(
            kind="quote",
            payload=Quote(symbol="AAPL", ts=datetime.now(tz=timezone.utc), price=Decimal("50")),
        )
        decision = portfolio.manage(event, [])

        assert len(decision.final_intents) == 2
        assert all(i.side == Side.SELL for i in decision.final_intents)
        assert all(i.reason == "risk_max_drawdown_flatten" for i in decision.final_intents)
        assert decision.pause_until is not None
        assert decision.audit is not None
        assert "risk_events" in decision.audit

    def test_manage_max_position_size_resizes_buy(self):
        """Test max position size resizes BUY intents exceeding limit."""
        portfolio = SimplePortfolio(
            max_drawdown=Decimal("1.0"),  # Disable drawdown check
            max_position_fraction=Decimal("0.25"),  # 25% max
        )
        portfolio.equity.cash = Decimal("100000")
        portfolio.equity.update_price("AAPL", Decimal("100"))
        portfolio.equity.refresh()

        event = MarketEvent(
            kind="quote",
            payload=Quote(symbol="AAPL", ts=datetime.now(tz=timezone.utc), price=Decimal("100")),
        )
        # Try to buy $50k worth (500 shares) but max is $25k (250 shares)
        intents = [OrderIntent(symbol="AAPL", side=Side.BUY, qty=Decimal("500"), reason="test")]
        decision = portfolio.manage(event, intents)

        assert len(decision.final_intents) == 1
        assert decision.final_intents[0].qty == Decimal("250")
        assert decision.audit is not None
        assert "resized" in decision.audit
        assert any(r["reason"] == "max_position_size" for r in decision.audit["resized"])

    def test_manage_max_gross_exposure_resizes_buy(self):
        """Test max gross exposure resizes BUY intents when exposure limit reached."""
        portfolio = SimplePortfolio(
            max_drawdown=Decimal("1.0"),
            max_position_fraction=Decimal("1.0"),  # No position limit
            max_gross_exposure_fraction=Decimal("0.50"),  # 50% max exposure
        )
        # Existing position implies cash was spent; keep total equity at $100k.
        portfolio.equity.cash = Decimal("60000")
        portfolio.equity.positions_by_symbol["NVDA"] = Decimal("100")
        portfolio.equity.update_price("NVDA", Decimal("400"))  # $40k exposure
        portfolio.equity.update_price("AAPL", Decimal("100"))
        portfolio.equity.refresh()

        event = MarketEvent(
            kind="quote",
            payload=Quote(symbol="AAPL", ts=datetime.now(tz=timezone.utc), price=Decimal("100")),
        )
        # Try to buy $30k worth but only $10k remaining (50k max - 40k existing)
        intents = [OrderIntent(symbol="AAPL", side=Side.BUY, qty=Decimal("300"), reason="test")]
        decision = portfolio.manage(event, intents)

        assert len(decision.final_intents) == 1
        assert decision.final_intents[0].qty == Decimal("100")  # $10k / $100
        assert decision.audit is not None
        assert "resized" in decision.audit
        assert any(r["reason"] == "max_gross_exposure" for r in decision.audit["resized"])

    def test_manage_vetoes_intent_when_exposure_exceeded(self):
        """Test intents are vetoed when gross exposure already at limit."""
        portfolio = SimplePortfolio(
            max_drawdown=Decimal("1.0"),
            max_gross_exposure_fraction=Decimal("0.50"),
        )
        # Existing position implies cash was spent; keep total equity at $100k.
        portfolio.equity.cash = Decimal("50000")
        portfolio.equity.positions_by_symbol["NVDA"] = Decimal("125")
        portfolio.equity.update_price("NVDA", Decimal("400"))  # $50k exposure (at limit)
        portfolio.equity.update_price("AAPL", Decimal("100"))
        portfolio.equity.refresh()

        event = MarketEvent(
            kind="quote",
            payload=Quote(symbol="AAPL", ts=datetime.now(tz=timezone.utc), price=Decimal("100")),
        )
        intents = [OrderIntent(symbol="AAPL", side=Side.BUY, qty=Decimal("10"), reason="test")]
        decision = portfolio.manage(event, intents)

        assert len(decision.final_intents) == 0
        assert decision.audit is not None
        assert "vetoed" in decision.audit
        assert any(v["reason"] == "max_gross_exposure" for v in decision.audit["vetoed"])

    def test_manage_filters_disabled_symbols(self):
        """Test disabled symbols are filtered from final intents."""
        portfolio = SimplePortfolio()
        portfolio.disabled_symbols.add("AAPL")
        portfolio.equity.update_price("AAPL", Decimal("100"))
        portfolio.equity.refresh()

        event = MarketEvent(
            kind="quote",
            payload=Quote(symbol="AAPL", ts=datetime.now(tz=timezone.utc), price=Decimal("100")),
        )
        intents = [OrderIntent(symbol="AAPL", side=Side.BUY, qty=Decimal("10"), reason="test")]
        decision = portfolio.manage(event, intents)

        assert len(decision.final_intents) == 0

    def test_manage_gates_new_symbols_by_max_symbols(self):
        """Test max_symbols gate prevents opening new positions."""
        portfolio = SimplePortfolio(max_symbols=2)
        portfolio.equity.positions_by_symbol["SYM1"] = Decimal("10")
        portfolio.equity.positions_by_symbol["SYM2"] = Decimal("10")
        portfolio.equity.update_price("SYM3", Decimal("100"))
        portfolio.equity.refresh()

        event = MarketEvent(
            kind="quote",
            payload=Quote(symbol="SYM3", ts=datetime.now(tz=timezone.utc), price=Decimal("100")),
        )
        intents = [OrderIntent(symbol="SYM3", side=Side.BUY, qty=Decimal("10"), reason="test")]
        decision = portfolio.manage(event, intents)

        assert len(decision.final_intents) == 0

    def test_manage_allows_existing_symbols_beyond_max_symbols(self):
        """Test existing positions can be added to even if at max_symbols."""
        portfolio = SimplePortfolio(max_symbols=2)
        portfolio.equity.positions_by_symbol["AAPL"] = Decimal("10")
        portfolio.equity.positions_by_symbol["NVDA"] = Decimal("10")
        portfolio.equity.update_price("AAPL", Decimal("100"))
        portfolio.equity.refresh()

        event = MarketEvent(
            kind="quote",
            payload=Quote(symbol="AAPL", ts=datetime.now(tz=timezone.utc), price=Decimal("100")),
        )
        intents = [OrderIntent(symbol="AAPL", side=Side.BUY, qty=Decimal("10"), reason="test")]
        decision = portfolio.manage(event, intents)

        assert len(decision.final_intents) == 1

    def test_manage_vetoes_intent_without_price(self):
        """Test intents without reference price are vetoed."""
        portfolio = SimplePortfolio()
        event = MarketEvent(
            kind="quote",
            payload=Quote(symbol="UNKNOWN", ts=datetime.now(tz=timezone.utc), price=Decimal("100")),
        )
        intents = [OrderIntent(symbol="AAPL", side=Side.BUY, qty=Decimal("10"), reason="test")]
        decision = portfolio.manage(event, intents)

        assert len(decision.final_intents) == 0
        assert decision.audit is not None
        assert "vetoed" in decision.audit
        assert any(v["reason"] == "missing_price" for v in decision.audit["vetoed"])

    def test_manage_assigns_reference_price_from_event(self):
        """Test reference price is assigned from market event when missing."""
        portfolio = SimplePortfolio()
        portfolio.equity.update_price("AAPL", Decimal("100"))
        portfolio.equity.refresh()

        event = MarketEvent(
            kind="quote",
            payload=Quote(symbol="AAPL", ts=datetime.now(tz=timezone.utc), price=Decimal("150")),
        )
        intents = [OrderIntent(symbol="AAPL", side=Side.BUY, qty=Decimal("10"), reason="test")]
        decision = portfolio.manage(event, intents)

        assert len(decision.final_intents) == 1
        assert decision.final_intents[0].reference_price == Decimal("150")

    def test_apply_fill_detects_slippage_violation(self):
        """Test apply_fill detects slippage exceeding max_slippage_fraction."""
        portfolio = SimplePortfolio(max_slippage_fraction=Decimal("0.02"))  # 2% max
        portfolio._pending_reference_price_by_symbol["AAPL"] = Decimal("100")
        fill = Fill(
            symbol="AAPL",
            side=Side.BUY,
            qty=Decimal("10"),
            price=Decimal("105"),  # 5% slippage
            ts=datetime.now(tz=timezone.utc),
        )
        portfolio.apply_fill(fill)

        assert len(portfolio._pending_risk_events) == 1
        assert portfolio._pending_risk_events[0]["type"] == "slippage_violation"

    def test_apply_fill_sets_cooldown_after_loss(self):
        """Test apply_fill sets cooldown_until after realized loss."""
        portfolio = SimplePortfolio(cooldown_after_loss_seconds=60)
        portfolio.equity.positions_by_symbol["AAPL"] = Decimal("10")
        portfolio.equity.avg_cost_by_symbol["AAPL"] = Decimal("100")
        fill = Fill(
            symbol="AAPL",
            side=Side.SELL,
            qty=Decimal("10"),
            price=Decimal("80"),  # $20 loss
            ts=datetime.now(tz=timezone.utc),
        )
        portfolio.apply_fill(fill)

        assert portfolio.cooldown_until is not None
        assert portfolio.cooldown_until == fill.ts + timedelta(seconds=60)
        assert len(portfolio._pending_risk_events) == 1
        assert portfolio._pending_risk_events[0]["type"] == "cooldown_after_loss"

    def test_manage_respects_cooldown_until(self):
        """Test manage returns pause_until when cooldown is active."""
        portfolio = SimplePortfolio()
        future_time = datetime.now(tz=timezone.utc) + timedelta(seconds=300)
        portfolio.cooldown_until = future_time
        portfolio.equity.update_price("AAPL", Decimal("100"))
        portfolio.equity.refresh()

        event = MarketEvent(
            kind="quote",
            payload=Quote(symbol="AAPL", ts=datetime.now(tz=timezone.utc), price=Decimal("100")),
        )
        intents = [OrderIntent(symbol="AAPL", side=Side.BUY, qty=Decimal("10"), reason="test")]
        decision = portfolio.manage(event, intents)

        assert decision.pause_until == future_time
