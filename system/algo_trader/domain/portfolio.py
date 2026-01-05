from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from system.algo_trader.domain.events import OverrideEvent
from system.algo_trader.domain.equity import EquityTracker
from system.algo_trader.domain.events import MarketEvent
from system.algo_trader.domain.models import Fill, OrderIntent, Side
from system.algo_trader.ports.portfolio import PortfolioDecision
from system.algo_trader.ports.portfolio import PortfolioPort


@dataclass(slots=True)
class SimplePortfolio(PortfolioPort):
    """Minimal portfolio schema for backtest/forward-test.

    - Tracks positions by symbol
    - Allows CLI overrides to disable symbols or flatten
    """

    max_symbols: int = 200
    max_drawdown: Decimal = Decimal("0.10")
    max_position_fraction: Decimal = Decimal("0.25")
    max_gross_exposure_fraction: Decimal = Decimal("1.00")
    cooldown_after_loss_seconds: int = 0
    cooldown_after_drawdown_seconds: int = 300
    max_slippage_fraction: Decimal = Decimal("0.02")

    disabled_symbols: set[str] = field(default_factory=set)
    equity: EquityTracker = field(default_factory=EquityTracker)
    cooldown_until: datetime | None = None
    _pending_reference_price_by_symbol: dict[str, Decimal] = field(default_factory=dict)
    _pending_risk_events: list[dict[str, str]] = field(default_factory=list)

    def position(self, symbol: str) -> Decimal:
        """Return current position quantity for a symbol."""
        return self.equity.positions_by_symbol.get(symbol, Decimal("0"))

    def manage(self, event: MarketEvent, proposed_intents: Sequence[OrderIntent]) -> PortfolioDecision:
        """Transform proposed intents into final intents, updating equity curve state."""
        sym: str | None = None
        px: Decimal | None = None
        now: datetime
        if hasattr(event.payload, "symbol") and hasattr(event.payload, "price"):
            sym = getattr(event.payload, "symbol")
            px = getattr(event.payload, "price")
            now = getattr(event.payload, "ts", datetime.now(tz=timezone.utc))
        elif hasattr(event.payload, "symbol") and hasattr(event.payload, "close"):
            sym = getattr(event.payload, "symbol")
            px = getattr(event.payload, "close")
            now = datetime.now(tz=timezone.utc)
        else:
            now = datetime.now(tz=timezone.utc)

        if sym is not None and px is not None:
            self.equity.update_price(sym, px)
            dd = self.equity.refresh()
        else:
            dd = self.equity.refresh()

        eq = self.equity.last_equity
        peak = self.equity.peak_equity

        # Risk control: max drawdown -> flatten + pause.
        if self.max_drawdown > 0 and dd >= self.max_drawdown:
            flatten: list[OrderIntent] = []
            for s, qty in self.equity.positions_by_symbol.items():
                if qty > 0:
                    flatten.append(
                        OrderIntent(
                            symbol=s,
                            side=Side.SELL,
                            qty=qty,
                            reason="risk_max_drawdown_flatten",
                            reference_price=self.equity.latest_price_by_symbol.get(s),
                        )
                    )
            pause_until = now + timedelta(seconds=self.cooldown_after_drawdown_seconds)
            self._pending_risk_events.append(
                {
                    "type": "max_drawdown",
                    "drawdown": str(dd),
                    "equity": str(eq),
                    "peak_equity": str(peak),
                }
            )
            for i in flatten:
                if i.reference_price is not None:
                    self._pending_reference_price_by_symbol[i.symbol] = i.reference_price
            audit = {"risk_events": list(self._pending_risk_events)}
            self._pending_risk_events.clear()
            return PortfolioDecision(
                proposed_intents=tuple(proposed_intents),
                final_intents=tuple(flatten),
                pause_until=pause_until,
                audit=audit,
            )

        # Ensure proposed intents have a reference price when we have one.
        proposed: list[OrderIntent] = []
        for i in proposed_intents:
            if i.reference_price is None and px is not None and i.symbol == sym:
                proposed.append(
                    OrderIntent(
                        symbol=i.symbol,
                        side=i.side,
                        qty=i.qty,
                        reason=i.reason,
                        reference_price=px,
                    )
                )
            else:
                proposed.append(i)

        # Minimal rules (disabled symbols + max_symbols gate on new buys).
        gated: list[OrderIntent] = []
        open_symbols = set(self.equity.positions_by_symbol.keys())
        for intent in proposed:
            if intent.symbol in self.disabled_symbols:
                continue
            if intent.side == Side.BUY:
                if intent.symbol not in open_symbols and len(open_symbols) >= self.max_symbols:
                    continue
                open_symbols.add(intent.symbol)
            gated.append(intent)

        # Risk control: position sizing + gross exposure.
        final: list[OrderIntent] = []
        gross = Decimal("0")
        for s, qty in self.equity.positions_by_symbol.items():
            px_s = self.equity.latest_price_by_symbol.get(s)
            if px_s is None:
                continue
            if qty > 0:
                gross += qty * px_s

        audit: dict[str, object] = {}
        resized: list[dict[str, str]] = []
        vetoed: list[dict[str, str]] = []

        for intent in gated:
            rp = intent.reference_price or self.equity.latest_price_by_symbol.get(intent.symbol)
            if rp is None or rp <= 0:
                vetoed.append({"symbol": intent.symbol, "reason": "missing_price"})
                continue

            qty = intent.qty
            if intent.side == Side.BUY:
                max_pos_val = eq * self.max_position_fraction
                notional = qty * rp
                if self.max_position_fraction > 0 and notional > max_pos_val:
                    new_qty = max_pos_val / rp
                    if new_qty <= 0:
                        vetoed.append({"symbol": intent.symbol, "reason": "max_position_size"})
                        continue
                    resized.append(
                        {
                            "symbol": intent.symbol,
                            "reason": "max_position_size",
                            "from_qty": str(qty),
                            "to_qty": str(new_qty),
                        }
                    )
                    qty = new_qty

                max_gross = eq * self.max_gross_exposure_fraction
                remaining = max_gross - gross
                if self.max_gross_exposure_fraction > 0 and remaining <= 0:
                    vetoed.append({"symbol": intent.symbol, "reason": "max_gross_exposure"})
                    continue
                if self.max_gross_exposure_fraction > 0 and (qty * rp) > remaining:
                    new_qty = remaining / rp
                    if new_qty <= 0:
                        vetoed.append({"symbol": intent.symbol, "reason": "max_gross_exposure"})
                        continue
                    resized.append(
                        {
                            "symbol": intent.symbol,
                            "reason": "max_gross_exposure",
                            "from_qty": str(qty),
                            "to_qty": str(new_qty),
                        }
                    )
                    qty = new_qty

                gross += qty * rp

            # Track reference price for upcoming fills.
            self._pending_reference_price_by_symbol[intent.symbol] = rp
            final.append(
                OrderIntent(
                    symbol=intent.symbol,
                    side=intent.side,
                    qty=qty,
                    reason=intent.reason,
                    reference_price=rp,
                )
            )

        if resized:
            audit["resized"] = resized
        if vetoed:
            audit["vetoed"] = vetoed

        pause_until = self.cooldown_until if self.cooldown_until and self.cooldown_until > now else None
        if self._pending_risk_events:
            audit["risk_events"] = list(self._pending_risk_events)
            self._pending_risk_events.clear()

        return PortfolioDecision(
            proposed_intents=tuple(proposed),
            final_intents=tuple(final),
            pause_until=pause_until,
            audit=audit or None,
        )

    def apply_fill(self, fill: Fill) -> None:
        # Risk control: slippage audit (fill vs most recent intent reference).
        ref = self._pending_reference_price_by_symbol.pop(fill.symbol, None)
        if ref is not None and ref > 0 and self.max_slippage_fraction > 0:
            slip = abs(fill.price - ref) / ref
            if slip > self.max_slippage_fraction:
                self._pending_risk_events.append(
                    {
                        "type": "slippage_violation",
                        "symbol": fill.symbol,
                        "slippage": str(slip),
                        "reference_price": str(ref),
                        "fill_price": str(fill.price),
                    }
                )

        realized = self.equity.apply_fill(fill)
        if realized < 0 and self.cooldown_after_loss_seconds > 0:
            until = fill.ts + timedelta(seconds=self.cooldown_after_loss_seconds)
            if self.cooldown_until is None or until > self.cooldown_until:
                self.cooldown_until = until
            self._pending_risk_events.append(
                {
                    "type": "cooldown_after_loss",
                    "until": self.cooldown_until.isoformat(),
                    "realized_pnl": str(realized),
                }
            )
        _ = self.equity.refresh()

    def on_override(self, event: OverrideEvent) -> None:
        cmd = event.command.lower().strip()
        if cmd == "disable_symbol":
            sym = event.args.get("symbol")
            if sym:
                self.disabled_symbols.add(sym)
            return
        if cmd == "enable_symbol":
            sym = event.args.get("symbol")
            if sym:
                self.disabled_symbols.discard(sym)
            return
        if cmd == "flatten":
            # Portfolio-level flatten is handled by app/broker wiring (issue SELL intents).
            return
