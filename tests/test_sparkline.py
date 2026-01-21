"""Tests for sparkline generation utilities."""

import pytest

from tradfi.utils.sparkline import (
    SPARK_CHARS,
    format_large_number,
    sparkline,
    sparkline_with_label,
    trend_indicator,
)


class TestSparkline:
    """Test sparkline function."""

    def test_basic_sparkline(self):
        """Test basic sparkline generation."""
        values = [1, 2, 3, 4, 5]
        result = sparkline(values)
        assert len(result) == 5
        # First char should be lowest, last should be highest
        assert result[0] == SPARK_CHARS[0]
        assert result[-1] == SPARK_CHARS[7]

    def test_sparkline_with_declining_values(self):
        """Test sparkline with declining values."""
        values = [5, 4, 3, 2, 1]
        result = sparkline(values)
        assert len(result) == 5
        # First char should be highest, last should be lowest
        assert result[0] == SPARK_CHARS[7]
        assert result[-1] == SPARK_CHARS[0]

    def test_sparkline_all_same_values(self):
        """Test sparkline when all values are the same."""
        values = [10, 10, 10, 10]
        result = sparkline(values)
        assert len(result) == 4
        # All chars should be the middle char (index 4)
        assert all(c == SPARK_CHARS[4] for c in result)

    def test_sparkline_respects_width(self):
        """Test sparkline respects width parameter."""
        values = list(range(20))
        result = sparkline(values, width=10)
        # Should only show last 10 values
        assert len(result) == 10

    def test_sparkline_shorter_than_width(self):
        """Test sparkline when values < width."""
        values = [1, 2, 3]
        result = sparkline(values, width=10)
        assert len(result) == 3

    def test_sparkline_empty_values(self):
        """Test sparkline with empty values."""
        result = sparkline([])
        assert result == ""

    def test_sparkline_single_value(self):
        """Test sparkline with single value."""
        result = sparkline([50])
        assert len(result) == 1
        # Single value should use middle char
        assert result == SPARK_CHARS[4]

    def test_sparkline_two_values(self):
        """Test sparkline with two values."""
        result = sparkline([10, 20])
        assert len(result) == 2
        assert result[0] == SPARK_CHARS[0]  # Min
        assert result[1] == SPARK_CHARS[7]  # Max

    def test_sparkline_negative_values(self):
        """Test sparkline handles negative values."""
        values = [-10, -5, 0, 5, 10]
        result = sparkline(values)
        assert len(result) == 5
        # Should still range from min to max
        assert result[0] == SPARK_CHARS[0]  # Min (-10)
        assert result[-1] == SPARK_CHARS[7]  # Max (10)

    def test_sparkline_with_v_pattern(self):
        """Test sparkline with V-shaped pattern."""
        values = [10, 5, 2, 1, 2, 5, 10]
        result = sparkline(values)
        assert len(result) == 7
        # First and last should be highest
        assert result[0] == result[-1]
        # Middle should be lowest
        assert result[3] == SPARK_CHARS[0]


class TestSparklineWithLabel:
    """Test sparkline_with_label function."""

    def test_basic_labeled_sparkline(self):
        """Test sparkline with label."""
        values = [100, 110, 105, 120]
        result = sparkline_with_label(values, "Revenue")
        assert "Revenue:" in result
        assert "120" in result  # Latest value

    def test_labeled_sparkline_custom_formatter(self):
        """Test sparkline with custom format function."""
        values = [1_000_000_000, 1_200_000_000]
        result = sparkline_with_label(
            values, "Revenue",
            format_fn=lambda x: f"${x/1e9:.1f}B"
        )
        assert "Revenue:" in result
        assert "$1.2B" in result

    def test_labeled_sparkline_no_latest(self):
        """Test sparkline without showing latest value."""
        values = [100, 110, 120]
        result = sparkline_with_label(values, "Metric", show_latest=False)
        assert "Metric:" in result
        assert "120" not in result

    def test_labeled_sparkline_empty_values(self):
        """Test labeled sparkline with empty values."""
        result = sparkline_with_label([], "Revenue")
        assert result == "Revenue: N/A"

    def test_labeled_sparkline_respects_width(self):
        """Test labeled sparkline respects width."""
        values = list(range(1, 21))
        result = sparkline_with_label(values, "Data", width=5)
        # Count sparkline chars (should be 5)
        spark_chars_count = sum(1 for c in result if c in SPARK_CHARS)
        assert spark_chars_count == 5


class TestTrendIndicator:
    """Test trend_indicator function."""

    def test_upward_trend(self):
        """Test upward trend indicator."""
        values = [100, 110]  # 10% increase
        assert trend_indicator(values) == "↑"

    def test_downward_trend(self):
        """Test downward trend indicator."""
        values = [100, 90]  # 10% decrease
        assert trend_indicator(values) == "↓"

    def test_flat_trend(self):
        """Test flat trend indicator."""
        values = [100, 101]  # 1% change (within 3% threshold)
        assert trend_indicator(values) == "→"

    def test_trend_at_threshold(self):
        """Test trend at exactly 3% threshold."""
        values = [100, 103]  # Exactly 3%
        assert trend_indicator(values) == "→"

        values = [100, 103.01]  # Just over 3%
        assert trend_indicator(values) == "↑"

    def test_trend_insufficient_data(self):
        """Test trend with insufficient data."""
        assert trend_indicator([]) == "?"
        assert trend_indicator([100]) == "?"

    def test_trend_zero_prior(self):
        """Test trend handles zero prior value."""
        values = [0, 100]
        assert trend_indicator(values) == "?"

    def test_trend_negative_values(self):
        """Test trend with negative values."""
        values = [-100, -80]  # 20% improvement
        assert trend_indicator(values) == "↑"

    def test_trend_uses_last_two_values(self):
        """Test trend only considers last two values."""
        values = [50, 100, 110]  # Many ups, but last two are 100->110 (10%)
        assert trend_indicator(values) == "↑"


class TestSparklineFormatLargeNumber:
    """Test format_large_number in sparkline module."""

    def test_trillions(self):
        """Test formatting numbers in trillions."""
        assert format_large_number(1_500_000_000_000) == "$1.5T"

    def test_billions(self):
        """Test formatting numbers in billions."""
        assert format_large_number(1_500_000_000) == "$1.5B"
        assert format_large_number(10_000_000_000) == "$10.0B"

    def test_millions(self):
        """Test formatting numbers in millions."""
        assert format_large_number(1_500_000) == "$1.5M"
        assert format_large_number(500_000_000) == "$500.0M"

    def test_thousands(self):
        """Test formatting numbers in thousands."""
        assert format_large_number(1_500) == "$1.5K"
        assert format_large_number(50_000) == "$50.0K"

    def test_small_numbers(self):
        """Test formatting small numbers."""
        assert format_large_number(500) == "$500"
        assert format_large_number(99) == "$99"

    def test_none_value(self):
        """Test formatting None."""
        assert format_large_number(None) == "N/A"

    def test_negative_billions(self):
        """Test formatting negative numbers."""
        assert format_large_number(-1_500_000_000) == "-$1.5B"

    def test_negative_millions(self):
        """Test formatting negative millions."""
        assert format_large_number(-50_000_000) == "-$50.0M"


class TestSparkChars:
    """Test SPARK_CHARS constant."""

    def test_spark_chars_length(self):
        """Test SPARK_CHARS has 8 characters."""
        assert len(SPARK_CHARS) == 8

    def test_spark_chars_are_unicode_blocks(self):
        """Test SPARK_CHARS are Unicode block characters."""
        expected = "▁▂▃▄▅▆▇█"
        assert SPARK_CHARS == expected

    def test_spark_chars_ordered_by_height(self):
        """Test SPARK_CHARS are ordered by visual height."""
        # Just verify the known order
        assert SPARK_CHARS[0] == "▁"  # Lowest
        assert SPARK_CHARS[7] == "█"  # Highest


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
