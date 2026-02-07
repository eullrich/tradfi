"""Portfolio P&L and allocation calculations."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PositionMetrics:
    """Calculated metrics for a single position."""

    ticker: str
    shares: float
    entry_price: float
    current_price: float | None = None
    target_price: float | None = None
    notes: str | None = None
    thesis: str | None = None

    @property
    def cost_basis(self) -> float:
        """Total cost = shares * entry_price."""
        return self.shares * self.entry_price

    @property
    def current_value(self) -> float | None:
        """Current value = shares * current_price."""
        if self.current_price is None:
            return None
        return self.shares * self.current_price

    @property
    def gain_loss(self) -> float | None:
        """Absolute gain/loss in dollars."""
        if self.current_value is None:
            return None
        return self.current_value - self.cost_basis

    @property
    def gain_loss_pct(self) -> float | None:
        """Percentage gain/loss."""
        if self.gain_loss is None or self.cost_basis == 0:
            return None
        return (self.gain_loss / self.cost_basis) * 100

    @property
    def target_gain_pct(self) -> float | None:
        """Percentage gain to target price."""
        if self.target_price is None or self.entry_price == 0:
            return None
        return ((self.target_price - self.entry_price) / self.entry_price) * 100

    @property
    def distance_to_target_pct(self) -> float | None:
        """Percentage distance from current price to target."""
        if self.target_price is None or self.current_price is None or self.current_price == 0:
            return None
        return ((self.target_price - self.current_price) / self.current_price) * 100

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "ticker": self.ticker,
            "shares": self.shares,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "target_price": self.target_price,
            "cost_basis": self.cost_basis,
            "current_value": self.current_value,
            "gain_loss": self.gain_loss,
            "gain_loss_pct": self.gain_loss_pct,
            "target_gain_pct": self.target_gain_pct,
            "distance_to_target_pct": self.distance_to_target_pct,
            "notes": self.notes,
            "thesis": self.thesis,
        }


@dataclass
class PortfolioMetrics:
    """Aggregated metrics for a portfolio."""

    positions: list[PositionMetrics] = field(default_factory=list)

    @property
    def total_cost_basis(self) -> float:
        """Sum of all position cost bases."""
        return sum(p.cost_basis for p in self.positions)

    @property
    def total_current_value(self) -> float:
        """Sum of all position current values (0 if price unknown)."""
        return sum(p.current_value or 0 for p in self.positions)

    @property
    def total_gain_loss(self) -> float:
        """Total dollar gain/loss."""
        return self.total_current_value - self.total_cost_basis

    @property
    def total_gain_loss_pct(self) -> float | None:
        """Total percentage gain/loss."""
        if self.total_cost_basis == 0:
            return None
        return (self.total_gain_loss / self.total_cost_basis) * 100

    @property
    def position_count(self) -> int:
        """Number of positions."""
        return len(self.positions)

    def allocation_pct(self, position: PositionMetrics) -> float | None:
        """Calculate allocation % for a position based on current value."""
        if position.current_value is None or self.total_current_value == 0:
            return None
        return (position.current_value / self.total_current_value) * 100

    def cost_allocation_pct(self, position: PositionMetrics) -> float | None:
        """Calculate allocation % for a position based on cost basis."""
        if self.total_cost_basis == 0:
            return None
        return (position.cost_basis / self.total_cost_basis) * 100

    def to_dict(self, list_name: str | None = None) -> dict:
        """Convert to dictionary for API responses."""
        items = []
        for p in self.positions:
            item = p.to_dict()
            item["allocation_pct"] = self.allocation_pct(p)
            item["cost_allocation_pct"] = self.cost_allocation_pct(p)
            items.append(item)

        result = {
            "items": items,
            "total_cost_basis": self.total_cost_basis,
            "total_current_value": self.total_current_value,
            "total_gain_loss": self.total_gain_loss,
            "total_gain_loss_pct": self.total_gain_loss_pct,
            "position_count": self.position_count,
        }
        if list_name:
            result["list_name"] = list_name
        return result


def calculate_portfolio_metrics(
    positions: list[dict],
    current_prices: dict[str, float],
) -> PortfolioMetrics:
    """
    Calculate portfolio metrics from position data and current prices.

    Args:
        positions: List of position dicts with keys:
            - ticker: str
            - shares: float (optional)
            - entry_price: float (optional)
            - target_price: float (optional)
            - notes: str (optional)
            - thesis: str (optional)
        current_prices: Dict mapping ticker to current price

    Returns:
        PortfolioMetrics with all calculated values
    """
    position_metrics = []

    for pos in positions:
        shares = pos.get("shares")
        entry_price = pos.get("entry_price")

        # Skip items without position data
        if not shares or not entry_price:
            continue

        ticker = pos.get("ticker", "").upper()
        pm = PositionMetrics(
            ticker=ticker,
            shares=float(shares),
            entry_price=float(entry_price),
            current_price=current_prices.get(ticker),
            target_price=pos.get("target_price"),
            notes=pos.get("notes"),
            thesis=pos.get("thesis"),
        )
        position_metrics.append(pm)

    return PortfolioMetrics(positions=position_metrics)
