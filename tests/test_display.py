"""Tests for display utility functions."""

import pytest
from rich.text import Text

from tradfi.utils.display import (
    format_large_number,
    format_number,
    format_pct,
    get_margin_of_safety_display,
    get_rsi_display,
    get_signal_display,
)


class TestFormatNumber:
    """Test format_number function."""

    def test_basic_formatting(self):
        """Test basic number formatting."""
        assert format_number(123.456) == "123.46"
        assert format_number(1000.5) == "1,000.50"

    def test_custom_decimals(self):
        """Test formatting with custom decimal places."""
        assert format_number(123.456, decimals=0) == "123"
        assert format_number(123.456, decimals=1) == "123.5"
        assert format_number(123.456, decimals=3) == "123.456"

    def test_with_prefix(self):
        """Test formatting with prefix."""
        assert format_number(100.0, prefix="$") == "$100.00"
        assert format_number(1500.0, prefix="USD ") == "USD 1,500.00"

    def test_with_suffix(self):
        """Test formatting with suffix."""
        assert format_number(15.5, suffix="%") == "15.50%"
        assert format_number(100.0, suffix=" units") == "100.00 units"

    def test_with_prefix_and_suffix(self):
        """Test formatting with both prefix and suffix."""
        assert format_number(50.0, prefix="$", suffix=" CAD") == "$50.00 CAD"

    def test_none_value(self):
        """Test formatting None returns 'N/A'."""
        assert format_number(None) == "N/A"

    def test_zero_value(self):
        """Test formatting zero."""
        assert format_number(0.0) == "0.00"

    def test_negative_value(self):
        """Test formatting negative numbers."""
        assert format_number(-123.45) == "-123.45"

    def test_large_number(self):
        """Test formatting large numbers with thousands separator."""
        assert format_number(1234567.89) == "1,234,567.89"


class TestFormatPct:
    """Test format_pct function."""

    def test_positive_percentage(self):
        """Test formatting positive percentage."""
        assert format_pct(15.5) == "+15.5%"
        assert format_pct(100.0) == "+100.0%"

    def test_negative_percentage(self):
        """Test formatting negative percentage."""
        assert format_pct(-15.5) == "-15.5%"
        assert format_pct(-100.0) == "-100.0%"

    def test_zero_percentage(self):
        """Test formatting zero percentage (no sign)."""
        assert format_pct(0.0) == "0.0%"

    def test_custom_decimals(self):
        """Test formatting with custom decimal places."""
        assert format_pct(15.555, decimals=0) == "+16%"
        # Python uses banker's rounding (round half to even)
        # 15.555 with 2 decimals rounds to 15.55 (not 15.56)
        assert format_pct(15.556, decimals=2) == "+15.56%"

    def test_none_value(self):
        """Test formatting None returns 'N/A'."""
        assert format_pct(None) == "N/A"

    def test_small_percentage(self):
        """Test formatting small percentages."""
        assert format_pct(0.5) == "+0.5%"
        assert format_pct(-0.5) == "-0.5%"


class TestFormatLargeNumber:
    """Test format_large_number function."""

    def test_trillions(self):
        """Test formatting numbers in trillions."""
        assert format_large_number(1_500_000_000_000) == "$1.50T"
        assert format_large_number(2_000_000_000_000) == "$2.00T"

    def test_billions(self):
        """Test formatting numbers in billions."""
        assert format_large_number(1_500_000_000) == "$1.50B"
        assert format_large_number(10_000_000_000) == "$10.00B"
        assert format_large_number(500_000_000) == "$500.00M"  # Under $1B

    def test_millions(self):
        """Test formatting numbers in millions."""
        assert format_large_number(1_500_000) == "$1.50M"
        assert format_large_number(50_000_000) == "$50.00M"

    def test_thousands(self):
        """Test formatting numbers in thousands."""
        assert format_large_number(1_500) == "$1.50K"
        assert format_large_number(50_000) == "$50.00K"

    def test_small_numbers(self):
        """Test formatting numbers under 1000."""
        assert format_large_number(500) == "$500.00"
        assert format_large_number(99.99) == "$99.99"

    def test_none_value(self):
        """Test formatting None returns 'N/A'."""
        assert format_large_number(None) == "N/A"

    def test_negative_values(self):
        """Test formatting negative numbers."""
        assert format_large_number(-1_500_000_000) == "$-1.50B"
        assert format_large_number(-500_000) == "$-500.00K"


class TestGetSignalDisplay:
    """Test get_signal_display function."""

    def test_strong_buy_signal(self):
        """Test STRONG_BUY signal display."""
        result = get_signal_display("STRONG_BUY")
        assert isinstance(result, Text)
        assert str(result) == "STRONG BUY"
        assert result.style == "bold green"

    def test_buy_signal(self):
        """Test BUY signal display."""
        result = get_signal_display("BUY")
        assert isinstance(result, Text)
        assert str(result) == "BUY"
        assert result.style == "green"

    def test_watch_signal(self):
        """Test WATCH signal display."""
        result = get_signal_display("WATCH")
        assert isinstance(result, Text)
        assert str(result) == "WATCH"
        assert result.style == "yellow"

    def test_neutral_signal(self):
        """Test NEUTRAL signal display."""
        result = get_signal_display("NEUTRAL")
        assert isinstance(result, Text)
        assert str(result) == "NEUTRAL"
        assert result.style == "white"

    def test_no_signal(self):
        """Test NO_SIGNAL display."""
        result = get_signal_display("NO_SIGNAL")
        assert isinstance(result, Text)
        assert str(result) == "--"
        assert result.style == "dim"

    def test_unknown_signal(self):
        """Test unknown signal defaults to dim '--'."""
        result = get_signal_display("UNKNOWN")
        assert isinstance(result, Text)
        assert str(result) == "--"
        assert result.style == "dim"


class TestGetRSIDisplay:
    """Test get_rsi_display function."""

    def test_strongly_oversold_rsi(self):
        """Test RSI < 20 display (strongly oversold)."""
        result = get_rsi_display(15.0)
        assert isinstance(result, Text)
        assert "15.0" in str(result)
        assert "STRONGLY OVERSOLD" in str(result)
        assert result.style == "bold red"

    def test_oversold_rsi(self):
        """Test RSI 20-30 display (oversold)."""
        result = get_rsi_display(25.0)
        assert isinstance(result, Text)
        assert "25.0" in str(result)
        assert "OVERSOLD" in str(result)
        assert result.style == "red"

    def test_approaching_oversold_rsi(self):
        """Test RSI 30-40 display (approaching oversold)."""
        result = get_rsi_display(35.0)
        assert isinstance(result, Text)
        assert "35.0" in str(result)
        assert "APPROACHING OVERSOLD" in str(result)
        assert result.style == "yellow"

    def test_neutral_rsi(self):
        """Test RSI 40-60 display (neutral)."""
        result = get_rsi_display(50.0)
        assert isinstance(result, Text)
        assert "50.0" in str(result)
        assert "NEUTRAL" in str(result)
        assert result.style == "white"

    def test_approaching_overbought_rsi(self):
        """Test RSI 60-70 display (approaching overbought)."""
        result = get_rsi_display(65.0)
        assert isinstance(result, Text)
        assert "65.0" in str(result)
        assert "APPROACHING OVERBOUGHT" in str(result)
        assert result.style == "yellow"

    def test_overbought_rsi(self):
        """Test RSI >= 70 display (overbought)."""
        result = get_rsi_display(75.0)
        assert isinstance(result, Text)
        assert "75.0" in str(result)
        assert "OVERBOUGHT" in str(result)
        assert result.style == "red"

    def test_none_rsi(self):
        """Test None RSI display."""
        result = get_rsi_display(None)
        assert isinstance(result, Text)
        assert str(result) == "N/A"
        assert result.style == "dim"


class TestGetMarginOfSafetyDisplay:
    """Test get_margin_of_safety_display function."""

    def test_highly_undervalued(self):
        """Test MoS >= 30% display (highly undervalued)."""
        result = get_margin_of_safety_display(35.0)
        assert isinstance(result, Text)
        assert "+35.0%" in str(result)
        assert "UNDERVALUED" in str(result)
        assert result.style == "bold green"

    def test_moderately_undervalued(self):
        """Test MoS 10-30% display (moderately undervalued)."""
        result = get_margin_of_safety_display(20.0)
        assert isinstance(result, Text)
        assert "+20.0%" in str(result)
        assert "UNDERVALUED" in str(result)
        assert result.style == "green"

    def test_fair_value(self):
        """Test MoS 0-10% display (fair value)."""
        result = get_margin_of_safety_display(5.0)
        assert isinstance(result, Text)
        assert "+5.0%" in str(result)
        assert "FAIR VALUE" in str(result)
        assert result.style == "yellow"

    def test_slightly_overvalued(self):
        """Test MoS -10-0% display (slightly overvalued)."""
        result = get_margin_of_safety_display(-5.0)
        assert isinstance(result, Text)
        assert "-5.0%" in str(result)
        assert "SLIGHTLY OVERVALUED" in str(result)
        assert result.style == "yellow"

    def test_overvalued(self):
        """Test MoS < -10% display (overvalued)."""
        result = get_margin_of_safety_display(-20.0)
        assert isinstance(result, Text)
        assert "-20.0%" in str(result)
        assert "OVERVALUED" in str(result)
        assert result.style == "red"

    def test_none_mos(self):
        """Test None MoS display."""
        result = get_margin_of_safety_display(None)
        assert isinstance(result, Text)
        assert str(result) == "N/A"
        assert result.style == "dim"

    def test_zero_mos(self):
        """Test zero MoS (exactly fair value)."""
        result = get_margin_of_safety_display(0.0)
        assert isinstance(result, Text)
        assert "FAIR VALUE" in str(result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
