"""Tests for stock data models."""

import pytest

from tradfi.models.stock import (
    BuybackInfo,
    DividendInfo,
    FairValueEstimates,
    FinancialHealth,
    GrowthMetrics,
    ProfitabilityMetrics,
    QuarterlyData,
    QuarterlyTrends,
    Stock,
    TechnicalIndicators,
    ValuationMetrics,
)


class TestQuarterlyData:
    """Test QuarterlyData dataclass."""

    def test_create_quarterly_data(self):
        """Test creating a QuarterlyData instance."""
        data = QuarterlyData(
            quarter="2024Q3",
            revenue=50_000_000_000,
            net_income=12_000_000_000,
            gross_margin=45.0,
            net_margin=24.0,
            eps=1.50,
        )
        assert data.quarter == "2024Q3"
        assert data.revenue == 50_000_000_000
        assert data.net_income == 12_000_000_000
        assert data.gross_margin == 45.0
        assert data.eps == 1.50

    def test_quarterly_data_defaults(self):
        """Test QuarterlyData defaults to None for optional fields."""
        data = QuarterlyData(quarter="2024Q3")
        assert data.quarter == "2024Q3"
        assert data.revenue is None
        assert data.net_income is None
        assert data.gross_margin is None
        assert data.eps is None


class TestQuarterlyTrends:
    """Test QuarterlyTrends with computed properties."""

    def test_revenue_trend_growing(self):
        """Test revenue trend shows 'Growing' when recent > prior average."""
        quarters = [
            QuarterlyData(quarter="2024Q3", revenue=120),  # Recent (20% above avg)
            QuarterlyData(quarter="2024Q2", revenue=100),
            QuarterlyData(quarter="2024Q1", revenue=100),
            QuarterlyData(quarter="2023Q4", revenue=100),
        ]
        trends = QuarterlyTrends(quarters=quarters)
        assert trends.revenue_trend == "Growing"

    def test_revenue_trend_declining(self):
        """Test revenue trend shows 'Declining' when recent < prior average."""
        quarters = [
            QuarterlyData(quarter="2024Q3", revenue=80),  # Recent (20% below avg)
            QuarterlyData(quarter="2024Q2", revenue=100),
            QuarterlyData(quarter="2024Q1", revenue=100),
            QuarterlyData(quarter="2023Q4", revenue=100),
        ]
        trends = QuarterlyTrends(quarters=quarters)
        assert trends.revenue_trend == "Declining"

    def test_revenue_trend_stable(self):
        """Test revenue trend shows 'Stable' when recent ≈ prior average."""
        quarters = [
            QuarterlyData(quarter="2024Q3", revenue=100),  # Same as average
            QuarterlyData(quarter="2024Q2", revenue=100),
            QuarterlyData(quarter="2024Q1", revenue=100),
            QuarterlyData(quarter="2023Q4", revenue=100),
        ]
        trends = QuarterlyTrends(quarters=quarters)
        assert trends.revenue_trend == "Stable"

    def test_revenue_trend_insufficient_data(self):
        """Test revenue trend returns 'N/A' with insufficient data."""
        trends = QuarterlyTrends(quarters=[
            QuarterlyData(quarter="2024Q3", revenue=100),
        ])
        assert trends.revenue_trend == "N/A"

    def test_revenue_trend_no_data(self):
        """Test revenue trend returns 'N/A' with no quarters."""
        trends = QuarterlyTrends(quarters=[])
        assert trends.revenue_trend == "N/A"

    def test_revenue_trend_zero_prior(self):
        """Test revenue trend handles zero prior average."""
        quarters = [
            QuarterlyData(quarter="2024Q3", revenue=100),
            QuarterlyData(quarter="2024Q2", revenue=0),
        ]
        trends = QuarterlyTrends(quarters=quarters)
        # Should handle division by zero gracefully
        assert trends.revenue_trend == "N/A"

    def test_margin_trend_expanding(self):
        """Test margin trend shows 'Expanding' when margins improving."""
        quarters = [
            QuarterlyData(quarter="2024Q3", gross_margin=48.0),  # +3pp above avg
            QuarterlyData(quarter="2024Q2", gross_margin=45.0),
            QuarterlyData(quarter="2024Q1", gross_margin=45.0),
            QuarterlyData(quarter="2023Q4", gross_margin=45.0),
        ]
        trends = QuarterlyTrends(quarters=quarters)
        assert trends.margin_trend == "Expanding"

    def test_margin_trend_contracting(self):
        """Test margin trend shows 'Contracting' when margins declining."""
        quarters = [
            QuarterlyData(quarter="2024Q3", gross_margin=42.0),  # -3pp below avg
            QuarterlyData(quarter="2024Q2", gross_margin=45.0),
            QuarterlyData(quarter="2024Q1", gross_margin=45.0),
            QuarterlyData(quarter="2023Q4", gross_margin=45.0),
        ]
        trends = QuarterlyTrends(quarters=quarters)
        assert trends.margin_trend == "Contracting"

    def test_margin_trend_stable(self):
        """Test margin trend shows 'Stable' when margins unchanged."""
        quarters = [
            QuarterlyData(quarter="2024Q3", gross_margin=45.0),
            QuarterlyData(quarter="2024Q2", gross_margin=45.0),
            QuarterlyData(quarter="2024Q1", gross_margin=45.0),
        ]
        trends = QuarterlyTrends(quarters=quarters)
        assert trends.margin_trend == "Stable"

    def test_margin_trend_insufficient_data(self):
        """Test margin trend returns 'N/A' with insufficient data."""
        trends = QuarterlyTrends(quarters=[
            QuarterlyData(quarter="2024Q3", gross_margin=45.0),
        ])
        assert trends.margin_trend == "N/A"

    def test_latest_qoq_revenue_growth(self):
        """Test QoQ revenue growth calculation."""
        quarters = [
            QuarterlyData(quarter="2024Q3", revenue=110),  # 10% growth
            QuarterlyData(quarter="2024Q2", revenue=100),
        ]
        trends = QuarterlyTrends(quarters=quarters)
        assert trends.latest_qoq_revenue_growth == pytest.approx(10.0)

    def test_latest_qoq_revenue_growth_negative(self):
        """Test negative QoQ revenue growth calculation."""
        quarters = [
            QuarterlyData(quarter="2024Q3", revenue=90),  # -10% decline
            QuarterlyData(quarter="2024Q2", revenue=100),
        ]
        trends = QuarterlyTrends(quarters=quarters)
        assert trends.latest_qoq_revenue_growth == pytest.approx(-10.0)

    def test_latest_qoq_revenue_growth_insufficient_data(self):
        """Test QoQ growth returns None with insufficient data."""
        trends = QuarterlyTrends(quarters=[
            QuarterlyData(quarter="2024Q3", revenue=100),
        ])
        assert trends.latest_qoq_revenue_growth is None

    def test_latest_qoq_revenue_growth_zero_prior(self):
        """Test QoQ growth handles zero prior quarter."""
        quarters = [
            QuarterlyData(quarter="2024Q3", revenue=100),
            QuarterlyData(quarter="2024Q2", revenue=0),
        ]
        trends = QuarterlyTrends(quarters=quarters)
        assert trends.latest_qoq_revenue_growth is None

    def test_latest_qoq_earnings_growth(self):
        """Test QoQ earnings growth calculation."""
        quarters = [
            QuarterlyData(quarter="2024Q3", net_income=22),  # 10% growth
            QuarterlyData(quarter="2024Q2", net_income=20),
        ]
        trends = QuarterlyTrends(quarters=quarters)
        assert trends.latest_qoq_earnings_growth == pytest.approx(10.0)

    def test_latest_qoq_earnings_growth_from_negative(self):
        """Test QoQ earnings growth from negative (turnaround)."""
        quarters = [
            QuarterlyData(quarter="2024Q3", net_income=10),  # Turned profitable
            QuarterlyData(quarter="2024Q2", net_income=-5),
        ]
        trends = QuarterlyTrends(quarters=quarters)
        # (10 - (-5)) / abs(-5) * 100 = 15 / 5 * 100 = 300%
        assert trends.latest_qoq_earnings_growth == pytest.approx(300.0)

    def test_get_metric_values(self):
        """Test extracting values for a specific metric."""
        quarters = [
            QuarterlyData(quarter="2024Q3", revenue=100, eps=1.5),
            QuarterlyData(quarter="2024Q2", revenue=95, eps=1.4),
            QuarterlyData(quarter="2024Q1", revenue=90, eps=None),
        ]
        trends = QuarterlyTrends(quarters=quarters)

        revenues = trends.get_metric_values("revenue")
        assert revenues == [100, 95, 90]

        eps_values = trends.get_metric_values("eps")
        assert eps_values == [1.5, 1.4]  # None filtered out

    def test_get_metric_values_nonexistent(self):
        """Test get_metric_values for nonexistent metric."""
        quarters = [QuarterlyData(quarter="2024Q3")]
        trends = QuarterlyTrends(quarters=quarters)
        values = trends.get_metric_values("nonexistent")
        assert values == []


class TestTechnicalIndicators:
    """Test TechnicalIndicators properties."""

    def test_is_oversold_low_rsi(self):
        """Test is_oversold when RSI < 30."""
        tech = TechnicalIndicators(rsi_14=25.0)
        assert tech.is_oversold is True

    def test_is_oversold_near_52w_low(self):
        """Test is_oversold when near 52-week low."""
        tech = TechnicalIndicators(rsi_14=45.0, pct_from_52w_low=8.0)
        assert tech.is_oversold is True

    def test_is_oversold_false(self):
        """Test is_oversold returns False when not oversold."""
        tech = TechnicalIndicators(rsi_14=50.0, pct_from_52w_low=25.0)
        assert tech.is_oversold is False

    def test_is_oversold_none_values(self):
        """Test is_oversold with None values."""
        tech = TechnicalIndicators(rsi_14=None, pct_from_52w_low=None)
        assert tech.is_oversold is False

    def test_is_strongly_oversold(self):
        """Test is_strongly_oversold when RSI < 20."""
        tech = TechnicalIndicators(rsi_14=15.0)
        assert tech.is_strongly_oversold is True

    def test_is_strongly_oversold_false(self):
        """Test is_strongly_oversold returns False when RSI >= 20."""
        tech = TechnicalIndicators(rsi_14=25.0)
        assert tech.is_strongly_oversold is False

    def test_is_strongly_oversold_none(self):
        """Test is_strongly_oversold with None RSI."""
        tech = TechnicalIndicators(rsi_14=None)
        assert tech.is_strongly_oversold is False


class TestStock:
    """Test Stock dataclass and signal generation."""

    def create_stock(
        self,
        pe: float | None = 15.0,
        pb: float | None = 2.0,
        roe: float | None = 15.0,
        rsi: float | None = 50.0,
        pct_from_52w_low: float | None = 20.0,
    ) -> Stock:
        """Helper to create test stocks."""
        return Stock(
            ticker="TEST",
            name="Test Inc",
            current_price=100.0,
            valuation=ValuationMetrics(pe_trailing=pe, pb_ratio=pb),
            profitability=ProfitabilityMetrics(roe=roe),
            technical=TechnicalIndicators(rsi_14=rsi, pct_from_52w_low=pct_from_52w_low),
        )

    def test_signal_strong_buy(self):
        """Test STRONG_BUY signal for value stock with RSI < 20."""
        stock = self.create_stock(pe=12.0, pb=1.5, rsi=15.0)
        assert stock.signal == "STRONG_BUY"

    def test_signal_buy_oversold(self):
        """Test BUY signal for value stock with RSI < 30."""
        stock = self.create_stock(pe=12.0, pb=1.5, rsi=25.0)
        assert stock.signal == "BUY"

    def test_signal_buy_near_52w_low(self):
        """Test BUY signal for value stock near 52-week low."""
        stock = self.create_stock(pe=12.0, pb=1.5, rsi=45.0, pct_from_52w_low=8.0)
        assert stock.signal == "BUY"

    def test_signal_watch(self):
        """Test WATCH signal for value stock approaching oversold."""
        stock = self.create_stock(pe=12.0, pb=1.5, rsi=35.0, pct_from_52w_low=25.0)
        assert stock.signal == "WATCH"

    def test_signal_watch_near_low(self):
        """Test WATCH signal for value stock moderately near 52-week low."""
        stock = self.create_stock(pe=12.0, pb=1.5, rsi=50.0, pct_from_52w_low=15.0)
        assert stock.signal == "WATCH"

    def test_signal_neutral(self):
        """Test NEUTRAL signal for value stock not oversold."""
        stock = self.create_stock(pe=12.0, pb=1.5, rsi=55.0, pct_from_52w_low=30.0)
        assert stock.signal == "NEUTRAL"

    def test_signal_no_signal_high_pe(self):
        """Test NO_SIGNAL for non-value stock (high P/E)."""
        stock = self.create_stock(pe=25.0, pb=1.5, rsi=25.0)
        assert stock.signal == "NO_SIGNAL"

    def test_signal_no_signal_high_pb(self):
        """Test NO_SIGNAL for non-value stock (high P/B)."""
        stock = self.create_stock(pe=12.0, pb=4.0, rsi=25.0)
        assert stock.signal == "NO_SIGNAL"

    def test_signal_no_signal_none_pe(self):
        """Test NO_SIGNAL when P/E is None."""
        stock = self.create_stock(pe=None, pb=1.5, rsi=25.0)
        assert stock.signal == "NO_SIGNAL"

    def test_signal_no_signal_negative_pe(self):
        """Test NO_SIGNAL when P/E is negative."""
        stock = self.create_stock(pe=-5.0, pb=1.5, rsi=25.0)
        assert stock.signal == "NO_SIGNAL"

    def test_stock_defaults(self):
        """Test Stock has sensible defaults."""
        stock = Stock(ticker="TEST")
        assert stock.ticker == "TEST"
        assert stock.name is None
        assert stock.currency == "USD"
        assert isinstance(stock.valuation, ValuationMetrics)
        assert isinstance(stock.technical, TechnicalIndicators)


class TestValuationMetrics:
    """Test ValuationMetrics dataclass."""

    def test_create_valuation_metrics(self):
        """Test creating ValuationMetrics."""
        metrics = ValuationMetrics(
            pe_trailing=15.0,
            pe_forward=12.0,
            pb_ratio=2.5,
            ps_ratio=3.0,
            market_cap=100_000_000_000,
        )
        assert metrics.pe_trailing == 15.0
        assert metrics.pe_forward == 12.0
        assert metrics.pb_ratio == 2.5
        assert metrics.market_cap == 100_000_000_000

    def test_valuation_metrics_defaults(self):
        """Test ValuationMetrics defaults to None."""
        metrics = ValuationMetrics()
        assert metrics.pe_trailing is None
        assert metrics.pb_ratio is None
        assert metrics.market_cap is None


class TestProfitabilityMetrics:
    """Test ProfitabilityMetrics dataclass."""

    def test_create_profitability_metrics(self):
        """Test creating ProfitabilityMetrics."""
        metrics = ProfitabilityMetrics(
            gross_margin=45.0,
            operating_margin=25.0,
            net_margin=20.0,
            roe=18.0,
            roa=12.0,
        )
        assert metrics.gross_margin == 45.0
        assert metrics.net_margin == 20.0
        assert metrics.roe == 18.0


class TestFinancialHealth:
    """Test FinancialHealth dataclass."""

    def test_create_financial_health(self):
        """Test creating FinancialHealth."""
        health = FinancialHealth(
            current_ratio=2.5,
            quick_ratio=1.8,
            debt_to_equity=50.0,
            free_cash_flow=5_000_000_000,
        )
        assert health.current_ratio == 2.5
        assert health.debt_to_equity == 50.0
        assert health.free_cash_flow == 5_000_000_000


class TestDividendInfo:
    """Test DividendInfo dataclass."""

    def test_create_dividend_info(self):
        """Test creating DividendInfo."""
        dividends = DividendInfo(
            dividend_yield=2.5,
            dividend_rate=1.80,
            payout_ratio=35.0,
        )
        assert dividends.dividend_yield == 2.5
        assert dividends.payout_ratio == 35.0


class TestFairValueEstimates:
    """Test FairValueEstimates dataclass."""

    def test_create_fair_value_estimates(self):
        """Test creating FairValueEstimates."""
        estimates = FairValueEstimates(
            graham_number=120.0,
            dcf_value=150.0,
            pe_fair_value=135.0,
            margin_of_safety_pct=25.0,
        )
        assert estimates.graham_number == 120.0
        assert estimates.dcf_value == 150.0
        assert estimates.margin_of_safety_pct == 25.0


class TestBuybackInfo:
    """Test BuybackInfo dataclass."""

    def test_create_buyback_info(self):
        """Test creating BuybackInfo."""
        buyback = BuybackInfo(
            insider_ownership_pct=5.0,
            institutional_ownership_pct=75.0,
            fcf_yield_pct=4.5,
            shares_outstanding=1_000_000_000,
        )
        assert buyback.insider_ownership_pct == 5.0
        assert buyback.fcf_yield_pct == 4.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
