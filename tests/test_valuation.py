"""Tests for valuation calculation functions."""

import math

import pytest

from tradfi.core.valuation import (
    calculate_dcf_fair_value,
    calculate_earnings_power_value,
    calculate_graham_number,
    calculate_margin_of_safety,
    calculate_pe_fair_value,
)


class TestGrahamNumber:
    """Test Graham Number calculation."""

    def test_basic_calculation(self):
        """Test standard Graham Number formula: sqrt(22.5 * EPS * Book Value)."""
        # Example: EPS=10, Book Value=50 -> sqrt(22.5 * 10 * 50) = sqrt(11250) ≈ 106.07
        result = calculate_graham_number(eps=10, book_value=50)
        expected = math.sqrt(22.5 * 10 * 50)
        assert result == pytest.approx(expected, rel=1e-6)
        assert result == pytest.approx(106.066, rel=0.001)

    def test_high_values(self):
        """Test with high EPS and book value."""
        result = calculate_graham_number(eps=150, book_value=200)
        expected = math.sqrt(22.5 * 150 * 200)
        assert result == pytest.approx(expected, rel=1e-6)

    def test_small_values(self):
        """Test with small EPS and book value."""
        result = calculate_graham_number(eps=0.5, book_value=2)
        expected = math.sqrt(22.5 * 0.5 * 2)
        assert result == pytest.approx(expected, rel=1e-6)

    def test_none_eps(self):
        """Test with None EPS returns None."""
        result = calculate_graham_number(eps=None, book_value=50)
        assert result is None

    def test_none_book_value(self):
        """Test with None book value returns None."""
        result = calculate_graham_number(eps=10, book_value=None)
        assert result is None

    def test_both_none(self):
        """Test with both None returns None."""
        result = calculate_graham_number(eps=None, book_value=None)
        assert result is None

    def test_zero_eps(self):
        """Test with zero EPS returns None (unprofitable company)."""
        result = calculate_graham_number(eps=0, book_value=50)
        assert result is None

    def test_negative_eps(self):
        """Test with negative EPS returns None (loss-making company)."""
        result = calculate_graham_number(eps=-5, book_value=50)
        assert result is None

    def test_zero_book_value(self):
        """Test with zero book value returns None."""
        result = calculate_graham_number(eps=10, book_value=0)
        assert result is None

    def test_negative_book_value(self):
        """Test with negative book value returns None (negative equity)."""
        result = calculate_graham_number(eps=10, book_value=-20)
        assert result is None


class TestMarginOfSafety:
    """Test margin of safety calculation."""

    def test_undervalued_stock(self):
        """Test margin of safety for undervalued stock (positive MoS)."""
        # Fair value $100, price $75 -> (100-75)/75 * 100 = 33.33%
        result = calculate_margin_of_safety(current_price=75, fair_value=100)
        assert result == pytest.approx(33.333, rel=0.01)

    def test_fairly_valued(self):
        """Test margin of safety when price equals fair value."""
        result = calculate_margin_of_safety(current_price=100, fair_value=100)
        assert result == pytest.approx(0.0)

    def test_overvalued_stock(self):
        """Test margin of safety for overvalued stock (negative MoS)."""
        # Fair value $80, price $100 -> (80-100)/100 * 100 = -20%
        result = calculate_margin_of_safety(current_price=100, fair_value=80)
        assert result == pytest.approx(-20.0)

    def test_significantly_undervalued(self):
        """Test large margin of safety."""
        # Fair value $200, price $100 -> (200-100)/100 * 100 = 100%
        result = calculate_margin_of_safety(current_price=100, fair_value=200)
        assert result == pytest.approx(100.0)

    def test_none_fair_value(self):
        """Test with None fair value returns None."""
        result = calculate_margin_of_safety(current_price=100, fair_value=None)
        assert result is None

    def test_zero_price(self):
        """Test with zero price returns None (invalid)."""
        result = calculate_margin_of_safety(current_price=0, fair_value=100)
        assert result is None

    def test_negative_price(self):
        """Test with negative price returns None (invalid)."""
        result = calculate_margin_of_safety(current_price=-10, fair_value=100)
        assert result is None


class TestPEFairValue:
    """Test P/E-based fair value calculation."""

    def test_basic_calculation(self):
        """Test P/E fair value with default P/E of 15."""
        # EPS=10, target P/E=15 -> fair value = 10 * 15 = 150
        result = calculate_pe_fair_value(eps=10)
        assert result == pytest.approx(150.0)

    def test_custom_target_pe(self):
        """Test P/E fair value with custom target P/E."""
        # EPS=8, target P/E=20 -> fair value = 8 * 20 = 160
        result = calculate_pe_fair_value(eps=8, target_pe=20)
        assert result == pytest.approx(160.0)

    def test_high_eps(self):
        """Test with high EPS value."""
        result = calculate_pe_fair_value(eps=100, target_pe=15)
        assert result == pytest.approx(1500.0)

    def test_low_eps(self):
        """Test with low EPS value."""
        result = calculate_pe_fair_value(eps=0.5, target_pe=15)
        assert result == pytest.approx(7.5)

    def test_none_eps(self):
        """Test with None EPS returns None."""
        result = calculate_pe_fair_value(eps=None)
        assert result is None

    def test_zero_eps(self):
        """Test with zero EPS returns None."""
        result = calculate_pe_fair_value(eps=0)
        assert result is None

    def test_negative_eps(self):
        """Test with negative EPS returns None (loss-making)."""
        result = calculate_pe_fair_value(eps=-5)
        assert result is None


class TestDCFFairValue:
    """Test Discounted Cash Flow fair value calculation."""

    def test_basic_calculation(self):
        """Test basic DCF calculation with defaults."""
        # Default: 5% growth, 10% discount, 3% terminal, 10 years
        result = calculate_dcf_fair_value(
            free_cash_flow=1_000_000_000,  # $1B FCF
            shares_outstanding=100_000_000,  # 100M shares
        )
        assert result is not None
        assert result > 0

    def test_custom_parameters(self):
        """Test DCF with custom growth and discount rates."""
        result = calculate_dcf_fair_value(
            free_cash_flow=500_000_000,
            shares_outstanding=50_000_000,
            growth_rate=0.08,
            discount_rate=0.12,
            terminal_growth=0.02,
            years=5,
        )
        assert result is not None
        assert result > 0

    def test_higher_growth_means_higher_value(self):
        """Test that higher growth rate results in higher fair value."""
        base_params = {
            "free_cash_flow": 1_000_000_000,
            "shares_outstanding": 100_000_000,
            "discount_rate": 0.10,
            "terminal_growth": 0.03,
        }
        low_growth = calculate_dcf_fair_value(**base_params, growth_rate=0.03)
        high_growth = calculate_dcf_fair_value(**base_params, growth_rate=0.10)
        assert high_growth > low_growth

    def test_higher_discount_means_lower_value(self):
        """Test that higher discount rate results in lower fair value."""
        base_params = {
            "free_cash_flow": 1_000_000_000,
            "shares_outstanding": 100_000_000,
            "growth_rate": 0.05,
            "terminal_growth": 0.03,
        }
        low_discount = calculate_dcf_fair_value(**base_params, discount_rate=0.08)
        high_discount = calculate_dcf_fair_value(**base_params, discount_rate=0.15)
        assert high_discount < low_discount

    def test_none_fcf(self):
        """Test with None free cash flow returns None."""
        result = calculate_dcf_fair_value(free_cash_flow=None, shares_outstanding=100_000_000)
        assert result is None

    def test_none_shares(self):
        """Test with None shares outstanding returns None."""
        result = calculate_dcf_fair_value(free_cash_flow=1_000_000_000, shares_outstanding=None)
        assert result is None

    def test_zero_fcf(self):
        """Test with zero FCF returns None."""
        result = calculate_dcf_fair_value(free_cash_flow=0, shares_outstanding=100_000_000)
        assert result is None

    def test_negative_fcf(self):
        """Test with negative FCF returns None (cash burn)."""
        result = calculate_dcf_fair_value(
            free_cash_flow=-1_000_000_000, shares_outstanding=100_000_000
        )
        assert result is None

    def test_zero_shares(self):
        """Test with zero shares returns None."""
        result = calculate_dcf_fair_value(free_cash_flow=1_000_000_000, shares_outstanding=0)
        assert result is None

    def test_invalid_terminal_growth(self):
        """Test when terminal growth >= discount rate returns None."""
        # This would result in infinite value (Gordon Growth formula denominator = 0)
        result = calculate_dcf_fair_value(
            free_cash_flow=1_000_000_000,
            shares_outstanding=100_000_000,
            discount_rate=0.05,
            terminal_growth=0.05,  # Equal to discount rate
        )
        assert result is None

        result = calculate_dcf_fair_value(
            free_cash_flow=1_000_000_000,
            shares_outstanding=100_000_000,
            discount_rate=0.05,
            terminal_growth=0.08,  # Greater than discount rate
        )
        assert result is None


class TestEarningsPowerValue:
    """Test Earnings Power Value (Bruce Greenwald) calculation."""

    def test_basic_calculation(self):
        """Test basic EPV calculation."""
        # Operating income $1B, 100M shares, 21% tax, 10% CoC
        # EPV = (1B * 0.79) / 0.10 / 100M = 79
        result = calculate_earnings_power_value(
            operating_income=1_000_000_000,
            shares_outstanding=100_000_000,
        )
        expected = (1_000_000_000 * 0.79) / 0.10 / 100_000_000
        assert result == pytest.approx(expected)
        assert result == pytest.approx(79.0)

    def test_custom_tax_rate(self):
        """Test EPV with custom tax rate."""
        result = calculate_earnings_power_value(
            operating_income=1_000_000_000,
            shares_outstanding=100_000_000,
            tax_rate=0.25,  # 25% tax
        )
        expected = (1_000_000_000 * 0.75) / 0.10 / 100_000_000
        assert result == pytest.approx(expected)

    def test_custom_cost_of_capital(self):
        """Test EPV with custom cost of capital."""
        result = calculate_earnings_power_value(
            operating_income=1_000_000_000,
            shares_outstanding=100_000_000,
            cost_of_capital=0.08,  # 8% CoC
        )
        expected = (1_000_000_000 * 0.79) / 0.08 / 100_000_000
        assert result == pytest.approx(expected)

    def test_none_operating_income(self):
        """Test with None operating income returns None."""
        result = calculate_earnings_power_value(
            operating_income=None, shares_outstanding=100_000_000
        )
        assert result is None

    def test_none_shares(self):
        """Test with None shares returns None."""
        result = calculate_earnings_power_value(
            operating_income=1_000_000_000, shares_outstanding=None
        )
        assert result is None

    def test_zero_operating_income(self):
        """Test with zero operating income returns None."""
        result = calculate_earnings_power_value(operating_income=0, shares_outstanding=100_000_000)
        assert result is None

    def test_negative_operating_income(self):
        """Test with negative operating income returns None."""
        result = calculate_earnings_power_value(
            operating_income=-1_000_000_000, shares_outstanding=100_000_000
        )
        assert result is None

    def test_zero_shares(self):
        """Test with zero shares returns None."""
        result = calculate_earnings_power_value(
            operating_income=1_000_000_000, shares_outstanding=0
        )
        assert result is None

    def test_zero_cost_of_capital(self):
        """Test with zero cost of capital returns None (division by zero)."""
        result = calculate_earnings_power_value(
            operating_income=1_000_000_000,
            shares_outstanding=100_000_000,
            cost_of_capital=0,
        )
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
