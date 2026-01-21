"""Tests for stock screening logic."""

import pytest

from tradfi.core.screener import (
    PRESET_SCREENS,
    ScreenCriteria,
    calculate_similarity_score,
    find_similar_stocks,
    get_preset_screen,
    screen_stock,
)
from tradfi.models.stock import (
    BuybackInfo,
    DividendInfo,
    FinancialHealth,
    GrowthMetrics,
    ProfitabilityMetrics,
    Stock,
    TechnicalIndicators,
    ValuationMetrics,
)


def create_test_stock(
    ticker: str = "TEST",
    pe: float | None = 15.0,
    pb: float | None = 1.5,
    ps: float | None = 2.0,
    peg: float | None = 1.2,
    roe: float | None = 15.0,
    roa: float | None = 8.0,
    net_margin: float | None = 12.0,
    debt_equity: float | None = 50.0,
    current_ratio: float | None = 2.0,
    revenue_growth: float | None = 10.0,
    earnings_growth: float | None = 12.0,
    dividend_yield: float | None = 2.0,
    market_cap: float | None = 10_000_000_000,
    rsi: float | None = 50.0,
    pct_from_52w_low: float | None = 15.0,
    pct_from_52w_high: float | None = -10.0,
    price_vs_ma_200: float | None = 5.0,
    price_vs_ma_50: float | None = 2.0,
    fcf_yield: float | None = 5.0,
    insider_ownership: float | None = 10.0,
    sector: str | None = "Technology",
    industry: str | None = "Software",
    current_price: float | None = 100.0,
) -> Stock:
    """Create a test stock with customizable attributes."""
    return Stock(
        ticker=ticker,
        name=f"{ticker} Inc",
        sector=sector,
        industry=industry,
        current_price=current_price,
        valuation=ValuationMetrics(
            pe_trailing=pe,
            pb_ratio=pb,
            ps_ratio=ps,
            peg_ratio=peg,
            market_cap=market_cap,
        ),
        profitability=ProfitabilityMetrics(
            roe=roe,
            roa=roa,
            net_margin=net_margin,
        ),
        financial_health=FinancialHealth(
            debt_to_equity=debt_equity,
            current_ratio=current_ratio,
        ),
        growth=GrowthMetrics(
            revenue_growth_yoy=revenue_growth,
            earnings_growth_yoy=earnings_growth,
        ),
        dividends=DividendInfo(
            dividend_yield=dividend_yield,
        ),
        technical=TechnicalIndicators(
            rsi_14=rsi,
            pct_from_52w_low=pct_from_52w_low,
            pct_from_52w_high=pct_from_52w_high,
            price_vs_ma_200_pct=price_vs_ma_200,
            price_vs_ma_50_pct=price_vs_ma_50,
        ),
        buyback=BuybackInfo(
            fcf_yield_pct=fcf_yield,
            insider_ownership_pct=insider_ownership,
        ),
    )


class TestScreenStock:
    """Test individual stock screening against criteria."""

    def test_stock_passes_empty_criteria(self):
        """Stock should pass when no criteria are set."""
        stock = create_test_stock()
        criteria = ScreenCriteria()
        assert screen_stock(stock, criteria) is True

    # P/E Tests
    def test_pe_max_pass(self):
        """Stock with P/E below max should pass."""
        stock = create_test_stock(pe=12.0)
        criteria = ScreenCriteria(pe_max=15)
        assert screen_stock(stock, criteria) is True

    def test_pe_max_fail(self):
        """Stock with P/E above max should fail."""
        stock = create_test_stock(pe=20.0)
        criteria = ScreenCriteria(pe_max=15)
        assert screen_stock(stock, criteria) is False

    def test_pe_min_pass(self):
        """Stock with P/E above min should pass."""
        stock = create_test_stock(pe=45.0)
        criteria = ScreenCriteria(pe_min=40)
        assert screen_stock(stock, criteria) is True

    def test_pe_min_fail(self):
        """Stock with P/E below min should fail."""
        stock = create_test_stock(pe=35.0)
        criteria = ScreenCriteria(pe_min=40)
        assert screen_stock(stock, criteria) is False

    def test_pe_none_fails_pe_max(self):
        """Stock with None P/E should fail pe_max criteria."""
        stock = create_test_stock(pe=None)
        criteria = ScreenCriteria(pe_max=15)
        assert screen_stock(stock, criteria) is False

    def test_pe_zero_fails_pe_max(self):
        """Stock with zero P/E should fail pe_max criteria."""
        stock = create_test_stock(pe=0)
        criteria = ScreenCriteria(pe_max=15)
        assert screen_stock(stock, criteria) is False

    def test_pe_negative_fails_pe_max(self):
        """Stock with negative P/E should fail pe_max criteria."""
        stock = create_test_stock(pe=-10)
        criteria = ScreenCriteria(pe_max=15)
        assert screen_stock(stock, criteria) is False

    # P/B Tests
    def test_pb_max_pass(self):
        """Stock with P/B below max should pass."""
        stock = create_test_stock(pb=1.2)
        criteria = ScreenCriteria(pb_max=1.5)
        assert screen_stock(stock, criteria) is True

    def test_pb_max_fail(self):
        """Stock with P/B above max should fail."""
        stock = create_test_stock(pb=2.0)
        criteria = ScreenCriteria(pb_max=1.5)
        assert screen_stock(stock, criteria) is False

    def test_pb_none_fails_pb_max(self):
        """Stock with None P/B should fail pb_max criteria."""
        stock = create_test_stock(pb=None)
        criteria = ScreenCriteria(pb_max=1.5)
        assert screen_stock(stock, criteria) is False

    # P/E x P/B Product Test (Graham's Rule)
    def test_pe_pb_product_pass(self):
        """Stock with P/E * P/B below 22.5 should pass Graham criteria."""
        stock = create_test_stock(pe=10.0, pb=1.5)  # Product = 15
        criteria = ScreenCriteria(pe_pb_product_max=22.5)
        assert screen_stock(stock, criteria) is True

    def test_pe_pb_product_fail(self):
        """Stock with P/E * P/B above 22.5 should fail Graham criteria."""
        stock = create_test_stock(pe=15.0, pb=2.0)  # Product = 30
        criteria = ScreenCriteria(pe_pb_product_max=22.5)
        assert screen_stock(stock, criteria) is False

    def test_pe_pb_product_none_pe(self):
        """Stock with None P/E should fail pe_pb_product criteria."""
        stock = create_test_stock(pe=None, pb=1.5)
        criteria = ScreenCriteria(pe_pb_product_max=22.5)
        assert screen_stock(stock, criteria) is False

    # ROE Tests
    def test_roe_min_pass(self):
        """Stock with ROE above min should pass."""
        stock = create_test_stock(roe=20.0)
        criteria = ScreenCriteria(roe_min=15)
        assert screen_stock(stock, criteria) is True

    def test_roe_min_fail(self):
        """Stock with ROE below min should fail."""
        stock = create_test_stock(roe=10.0)
        criteria = ScreenCriteria(roe_min=15)
        assert screen_stock(stock, criteria) is False

    def test_roe_max_pass(self):
        """Stock with ROE below max should pass (for short screening)."""
        stock = create_test_stock(roe=8.0)
        criteria = ScreenCriteria(roe_max=10)
        assert screen_stock(stock, criteria) is True

    def test_roe_max_fail(self):
        """Stock with ROE above max should fail (for short screening)."""
        stock = create_test_stock(roe=15.0)
        criteria = ScreenCriteria(roe_max=10)
        assert screen_stock(stock, criteria) is False

    def test_roe_none_fails_roe_min(self):
        """Stock with None ROE should fail roe_min criteria."""
        stock = create_test_stock(roe=None)
        criteria = ScreenCriteria(roe_min=15)
        assert screen_stock(stock, criteria) is False

    # Net Margin Tests
    def test_margin_min_pass(self):
        """Stock with margin above min should pass."""
        stock = create_test_stock(net_margin=15.0)
        criteria = ScreenCriteria(margin_min=10)
        assert screen_stock(stock, criteria) is True

    def test_margin_min_fail(self):
        """Stock with margin below min should fail."""
        stock = create_test_stock(net_margin=5.0)
        criteria = ScreenCriteria(margin_min=10)
        assert screen_stock(stock, criteria) is False

    # Debt/Equity Tests
    def test_debt_equity_max_pass(self):
        """Stock with D/E below max should pass."""
        stock = create_test_stock(debt_equity=40.0)  # D/E ratio in percentage
        criteria = ScreenCriteria(debt_equity_max=50)
        assert screen_stock(stock, criteria) is True

    def test_debt_equity_max_fail(self):
        """Stock with D/E above max should fail."""
        stock = create_test_stock(debt_equity=60.0)
        criteria = ScreenCriteria(debt_equity_max=50)
        assert screen_stock(stock, criteria) is False

    def test_debt_equity_none_passes(self):
        """Stock with None D/E should pass (allow missing data)."""
        stock = create_test_stock(debt_equity=None)
        criteria = ScreenCriteria(debt_equity_max=50)
        assert screen_stock(stock, criteria) is True

    # Current Ratio Tests
    def test_current_ratio_min_pass(self):
        """Stock with current ratio above min should pass."""
        stock = create_test_stock(current_ratio=2.5)
        criteria = ScreenCriteria(current_ratio_min=2.0)
        assert screen_stock(stock, criteria) is True

    def test_current_ratio_min_fail(self):
        """Stock with current ratio below min should fail."""
        stock = create_test_stock(current_ratio=1.5)
        criteria = ScreenCriteria(current_ratio_min=2.0)
        assert screen_stock(stock, criteria) is False

    # Dividend Yield Tests
    def test_dividend_yield_min_pass(self):
        """Stock with dividend yield above min should pass."""
        stock = create_test_stock(dividend_yield=4.0)
        criteria = ScreenCriteria(dividend_yield_min=3.0)
        assert screen_stock(stock, criteria) is True

    def test_dividend_yield_min_fail(self):
        """Stock with dividend yield below min should fail."""
        stock = create_test_stock(dividend_yield=2.0)
        criteria = ScreenCriteria(dividend_yield_min=3.0)
        assert screen_stock(stock, criteria) is False

    # Market Cap Tests
    def test_market_cap_min_pass(self):
        """Stock with market cap above min should pass."""
        stock = create_test_stock(market_cap=2_000_000_000)
        criteria = ScreenCriteria(market_cap_min=1_000_000_000)
        assert screen_stock(stock, criteria) is True

    def test_market_cap_min_fail(self):
        """Stock with market cap below min should fail."""
        stock = create_test_stock(market_cap=500_000_000)
        criteria = ScreenCriteria(market_cap_min=1_000_000_000)
        assert screen_stock(stock, criteria) is False

    def test_market_cap_max_pass(self):
        """Stock with market cap below max should pass."""
        stock = create_test_stock(market_cap=5_000_000_000)
        criteria = ScreenCriteria(market_cap_max=10_000_000_000)
        assert screen_stock(stock, criteria) is True

    def test_market_cap_max_fail(self):
        """Stock with market cap above max should fail."""
        stock = create_test_stock(market_cap=15_000_000_000)
        criteria = ScreenCriteria(market_cap_max=10_000_000_000)
        assert screen_stock(stock, criteria) is False

    # RSI Tests
    def test_rsi_max_pass(self):
        """Stock with RSI below max should pass (oversold screening)."""
        stock = create_test_stock(rsi=28.0)
        criteria = ScreenCriteria(rsi_max=35)
        assert screen_stock(stock, criteria) is True

    def test_rsi_max_fail(self):
        """Stock with RSI above max should fail."""
        stock = create_test_stock(rsi=50.0)
        criteria = ScreenCriteria(rsi_max=35)
        assert screen_stock(stock, criteria) is False

    def test_rsi_min_pass(self):
        """Stock with RSI above min should pass (overbought screening)."""
        stock = create_test_stock(rsi=65.0)
        criteria = ScreenCriteria(rsi_min=60)
        assert screen_stock(stock, criteria) is True

    def test_rsi_min_fail(self):
        """Stock with RSI below min should fail."""
        stock = create_test_stock(rsi=55.0)
        criteria = ScreenCriteria(rsi_min=60)
        assert screen_stock(stock, criteria) is False

    def test_rsi_none_fails(self):
        """Stock with None RSI should fail RSI criteria."""
        stock = create_test_stock(rsi=None)
        criteria = ScreenCriteria(rsi_max=35)
        assert screen_stock(stock, criteria) is False

    # 52-Week Low Proximity Tests
    def test_near_52w_low_pass(self):
        """Stock near 52-week low should pass."""
        stock = create_test_stock(pct_from_52w_low=10.0)
        criteria = ScreenCriteria(near_52w_low_pct=20)
        assert screen_stock(stock, criteria) is True

    def test_near_52w_low_fail(self):
        """Stock far from 52-week low should fail."""
        stock = create_test_stock(pct_from_52w_low=30.0)
        criteria = ScreenCriteria(near_52w_low_pct=20)
        assert screen_stock(stock, criteria) is False

    # Below Moving Average Tests
    def test_below_200ma_pass(self):
        """Stock below 200 MA should pass."""
        stock = create_test_stock(price_vs_ma_200=-5.0)
        criteria = ScreenCriteria(below_200ma=True)
        assert screen_stock(stock, criteria) is True

    def test_below_200ma_fail(self):
        """Stock above 200 MA should fail."""
        stock = create_test_stock(price_vs_ma_200=5.0)
        criteria = ScreenCriteria(below_200ma=True)
        assert screen_stock(stock, criteria) is False

    def test_below_50ma_pass(self):
        """Stock below 50 MA should pass."""
        stock = create_test_stock(price_vs_ma_50=-3.0)
        criteria = ScreenCriteria(below_50ma=True)
        assert screen_stock(stock, criteria) is True

    def test_below_50ma_fail(self):
        """Stock above 50 MA should fail."""
        stock = create_test_stock(price_vs_ma_50=3.0)
        criteria = ScreenCriteria(below_50ma=True)
        assert screen_stock(stock, criteria) is False

    # FCF Yield Tests
    def test_fcf_yield_min_pass(self):
        """Stock with FCF yield above min should pass."""
        stock = create_test_stock(fcf_yield=5.0)
        criteria = ScreenCriteria(fcf_yield_min=3.0)
        assert screen_stock(stock, criteria) is True

    def test_fcf_yield_min_fail(self):
        """Stock with FCF yield below min should fail."""
        stock = create_test_stock(fcf_yield=2.0)
        criteria = ScreenCriteria(fcf_yield_min=3.0)
        assert screen_stock(stock, criteria) is False

    # Combined Criteria Tests
    def test_graham_preset_pass(self):
        """Stock passing all Graham criteria should pass."""
        stock = create_test_stock(
            pe=12.0,
            pb=1.2,
            current_ratio=2.5,
            debt_equity=40.0,
        )
        criteria = ScreenCriteria(
            pe_max=15,
            pb_max=1.5,
            pe_pb_product_max=22.5,
            current_ratio_min=2.0,
            debt_equity_max=50,
        )
        assert screen_stock(stock, criteria) is True

    def test_graham_preset_fail_one_criteria(self):
        """Stock failing one Graham criterion should fail."""
        stock = create_test_stock(
            pe=12.0,
            pb=2.0,  # Fails P/B max of 1.5
            current_ratio=2.5,
            debt_equity=40.0,
        )
        criteria = ScreenCriteria(
            pe_max=15,
            pb_max=1.5,
            current_ratio_min=2.0,
            debt_equity_max=50,
        )
        assert screen_stock(stock, criteria) is False


class TestPresetScreens:
    """Test preset screen definitions."""

    def test_all_presets_exist(self):
        """All documented presets should exist."""
        expected_presets = [
            "graham",
            "buffett",
            "deep-value",
            "oversold-value",
            "dividend",
            "quality",
            "buyback",
            "short-candidates",
            "fallen-angels",
            "dividend-growers",
            "turnaround",
            "hidden-gems",
            "momentum-value",
        ]
        for preset in expected_presets:
            assert preset in PRESET_SCREENS, f"Preset '{preset}' not found"

    def test_get_preset_screen_valid(self):
        """get_preset_screen should return criteria for valid presets."""
        criteria = get_preset_screen("graham")
        assert isinstance(criteria, ScreenCriteria)
        assert criteria.pe_max == 15
        assert criteria.pb_max == 1.5

    def test_get_preset_screen_invalid(self):
        """get_preset_screen should raise ValueError for invalid preset."""
        with pytest.raises(ValueError, match="Unknown preset"):
            get_preset_screen("invalid_preset")

    def test_get_preset_screen_with_underscores(self):
        """get_preset_screen should handle underscores in preset names."""
        criteria = get_preset_screen("deep_value")
        assert criteria.pb_max == 1.0
        assert criteria.pe_max == 10

    def test_graham_preset_criteria(self):
        """Verify Graham preset has correct criteria."""
        criteria = PRESET_SCREENS["graham"]
        assert criteria.pe_max == 15
        assert criteria.pb_max == 1.5
        assert criteria.pe_pb_product_max == 22.5
        assert criteria.current_ratio_min == 2.0
        assert criteria.debt_equity_max == 50

    def test_buffett_preset_criteria(self):
        """Verify Buffett preset has correct criteria."""
        criteria = PRESET_SCREENS["buffett"]
        assert criteria.roe_min == 15
        assert criteria.debt_equity_max == 50
        assert criteria.margin_min == 10
        assert criteria.pe_max == 25

    def test_deep_value_preset_criteria(self):
        """Verify deep-value preset has correct criteria."""
        criteria = PRESET_SCREENS["deep-value"]
        assert criteria.pb_max == 1.0
        assert criteria.pe_max == 10

    def test_short_candidates_preset_criteria(self):
        """Verify short-candidates preset has correct criteria."""
        criteria = PRESET_SCREENS["short-candidates"]
        assert criteria.pe_min == 40
        assert criteria.roe_max == 10
        assert criteria.rsi_min == 60


class TestSimilarityScore:
    """Test stock similarity scoring."""

    def test_self_similarity_returns_zero(self):
        """Comparing a stock to itself should return 0."""
        stock = create_test_stock(ticker="AAPL")
        score, reasons = calculate_similarity_score(stock, stock)
        assert score == 0
        assert reasons == []

    def test_same_industry_match(self):
        """Stocks in same industry should get 30 points."""
        target = create_test_stock(ticker="AAPL", industry="Software", sector="Technology")
        candidate = create_test_stock(ticker="MSFT", industry="Software", sector="Technology")
        score, reasons = calculate_similarity_score(target, candidate)
        assert "Same industry" in reasons
        assert score >= 30

    def test_same_sector_different_industry(self):
        """Stocks in same sector but different industry should get 10 points."""
        target = create_test_stock(ticker="AAPL", industry="Hardware", sector="Technology")
        candidate = create_test_stock(ticker="MSFT", industry="Software", sector="Technology")
        score, reasons = calculate_similarity_score(target, candidate)
        assert "Same sector" in reasons
        assert score >= 10

    def test_similar_market_cap(self):
        """Stocks with similar market cap should get points."""
        target = create_test_stock(ticker="AAPL", market_cap=10_000_000_000)
        candidate = create_test_stock(ticker="MSFT", market_cap=12_000_000_000)
        score, reasons = calculate_similarity_score(target, candidate)
        assert "Similar size" in reasons

    def test_similar_pe_ratio(self):
        """Stocks with similar P/E should get points."""
        target = create_test_stock(ticker="AAPL", pe=15.0)
        candidate = create_test_stock(ticker="MSFT", pe=16.5)
        score, reasons = calculate_similarity_score(target, candidate)
        assert "Similar P/E" in reasons

    def test_similar_roe(self):
        """Stocks with similar ROE should get points."""
        target = create_test_stock(ticker="AAPL", roe=18.0)
        candidate = create_test_stock(ticker="MSFT", roe=19.5)
        score, reasons = calculate_similarity_score(target, candidate)
        assert "Similar ROE" in reasons

    def test_similar_dividend_yield(self):
        """Stocks with similar dividend yield should get points."""
        target = create_test_stock(ticker="AAPL", dividend_yield=2.0)
        candidate = create_test_stock(ticker="MSFT", dividend_yield=2.3)
        score, reasons = calculate_similarity_score(target, candidate)
        assert "Similar dividend" in reasons

    def test_both_non_dividend(self):
        """Two non-dividend stocks should get some points."""
        target = create_test_stock(ticker="AAPL", dividend_yield=None)
        candidate = create_test_stock(ticker="AMZN", dividend_yield=None)
        score, reasons = calculate_similarity_score(target, candidate)
        # Should get 5 points for both being non-dividend payers
        assert score >= 5

    def test_similar_momentum(self):
        """Stocks with similar RSI should get points."""
        target = create_test_stock(ticker="AAPL", rsi=45.0)
        candidate = create_test_stock(ticker="MSFT", rsi=47.0)
        score, reasons = calculate_similarity_score(target, candidate)
        assert "Similar momentum" in reasons


class TestFindSimilarStocks:
    """Test finding similar stocks."""

    def test_find_similar_returns_sorted_by_score(self):
        """Results should be sorted by similarity score descending."""
        target = create_test_stock(
            ticker="AAPL",
            industry="Software",
            sector="Technology",
            pe=15.0,
            market_cap=10_000_000_000,
        )
        candidates = [
            create_test_stock(ticker="MSFT", industry="Software", sector="Technology", pe=15.5),
            create_test_stock(ticker="GOOGL", industry="Internet", sector="Technology", pe=20.0),
            create_test_stock(ticker="JPM", industry="Banking", sector="Finance", pe=10.0),
        ]
        results = find_similar_stocks(target, candidates, limit=10, min_score=0)

        # Should be sorted by score descending
        scores = [score for _, score, _ in results]
        assert scores == sorted(scores, reverse=True)

    def test_find_similar_respects_limit(self):
        """Results should be limited to specified count."""
        target = create_test_stock(ticker="AAPL")
        candidates = [
            create_test_stock(ticker=f"STOCK{i}", industry="Software")
            for i in range(20)
        ]
        results = find_similar_stocks(target, candidates, limit=5, min_score=0)
        assert len(results) <= 5

    def test_find_similar_respects_min_score(self):
        """Results should only include stocks above min_score."""
        target = create_test_stock(
            ticker="AAPL",
            industry="Software",
            sector="Technology",
        )
        candidates = [
            create_test_stock(ticker="MSFT", industry="Software", sector="Technology"),  # High score
            create_test_stock(ticker="JPM", industry="Banking", sector="Finance"),  # Low score
        ]
        results = find_similar_stocks(target, candidates, limit=10, min_score=25)

        # All results should have score >= 25
        for _, score, _ in results:
            assert score >= 25

    def test_find_similar_excludes_target(self):
        """Target stock should not appear in results (score is 0 for self)."""
        target = create_test_stock(ticker="AAPL", industry="Software", sector="Technology")
        candidates = [target, create_test_stock(ticker="MSFT", industry="Software", sector="Technology")]
        # Use min_score > 0 to exclude self-matches (which return score 0)
        results = find_similar_stocks(target, candidates, limit=10, min_score=1)

        tickers = [stock.ticker for stock, _, _ in results]
        assert "AAPL" not in tickers

    def test_find_similar_empty_candidates(self):
        """Empty candidates should return empty results."""
        target = create_test_stock(ticker="AAPL")
        results = find_similar_stocks(target, [], limit=10, min_score=0)
        assert results == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
