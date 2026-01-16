"""ASCII sparkline generation for terminal trend visualization."""

# Unicode block characters for sparklines (increasing height)
SPARK_CHARS = "▁▂▃▄▅▆▇█"


def sparkline(values: list[float], width: int = 10) -> str:
    """
    Generate an ASCII sparkline from a list of values.

    Args:
        values: List of numeric values to visualize
        width: Maximum width of the sparkline (default 10)

    Returns:
        String of Unicode block characters representing the trend

    Example:
        >>> sparkline([1, 2, 3, 5, 8, 5, 3, 2, 1])
        '▁▂▃▅█▅▃▂▁'
    """
    if not values:
        return ""

    # Take the most recent 'width' values
    values = values[-width:]

    min_val = min(values)
    max_val = max(values)

    # Handle case where all values are the same
    if max_val == min_val:
        return SPARK_CHARS[4] * len(values)

    # Normalize values to 0-7 range (8 levels of block characters)
    result = []
    for val in values:
        normalized = (val - min_val) / (max_val - min_val)
        index = int(normalized * 7)
        index = min(7, max(0, index))  # Clamp to valid range
        result.append(SPARK_CHARS[index])

    return "".join(result)


def sparkline_with_label(
    values: list[float],
    label: str,
    width: int = 10,
    show_latest: bool = True,
    format_fn: callable = None
) -> str:
    """
    Generate a sparkline with a label and optional latest value.

    Args:
        values: List of numeric values to visualize
        label: Label to show before the sparkline
        width: Maximum width of the sparkline
        show_latest: Whether to show the most recent value
        format_fn: Optional function to format the latest value

    Returns:
        Formatted string like "Revenue:  $42.1B  ▁▂▃▄▅▆▇█"
    """
    if not values:
        return f"{label}: N/A"

    spark = sparkline(values, width)
    latest = values[-1] if values else None

    if show_latest and latest is not None:
        if format_fn:
            formatted = format_fn(latest)
        else:
            formatted = f"{latest:,.0f}"
        return f"{label}: {formatted}  {spark}"

    return f"{label}: {spark}"


def format_large_number(value: float) -> str:
    """Format a large number with B/M/K suffix."""
    if value is None:
        return "N/A"

    abs_val = abs(value)
    sign = "-" if value < 0 else ""

    if abs_val >= 1_000_000_000_000:
        return f"{sign}${abs_val / 1_000_000_000_000:.1f}T"
    elif abs_val >= 1_000_000_000:
        return f"{sign}${abs_val / 1_000_000_000:.1f}B"
    elif abs_val >= 1_000_000:
        return f"{sign}${abs_val / 1_000_000:.1f}M"
    elif abs_val >= 1_000:
        return f"{sign}${abs_val / 1_000:.1f}K"
    else:
        return f"{sign}${abs_val:.0f}"


def trend_indicator(values: list[float]) -> str:
    """
    Return a simple trend indicator based on recent values.

    Returns one of: "↑" (up), "↓" (down), "→" (flat), or "?" (insufficient data)
    """
    if len(values) < 2:
        return "?"

    recent = values[-1]
    prior = values[-2]

    if prior == 0:
        return "?"

    change_pct = ((recent - prior) / abs(prior)) * 100

    if change_pct > 3:
        return "↑"
    elif change_pct < -3:
        return "↓"
    else:
        return "→"
