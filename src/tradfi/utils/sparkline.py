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


# Bar characters for heatmap intensity (increasing density)
BAR_CHARS = "░▒▓█"


def ascii_bar(
    value: float,
    min_val: float,
    max_val: float,
    width: int = 14,
    reverse: bool = False,
) -> str:
    """
    Render an intensity bar using block characters.

    Args:
        value: The value to represent
        min_val: Minimum value in the range
        max_val: Maximum value in the range
        width: Total width of the bar
        reverse: If True, lower values get more filled bars (for P/E where low is good)

    Returns:
        String of block characters representing intensity

    Example:
        >>> ascii_bar(50, 0, 100, width=10)
        '█████░░░░░'
    """
    if max_val == min_val:
        return BAR_CHARS[2] * width

    # Normalize to 0-1
    normalized = (value - min_val) / (max_val - min_val)
    normalized = max(0, min(1, normalized))  # Clamp

    if reverse:
        normalized = 1 - normalized

    # Calculate filled portion
    filled = int(normalized * width)
    empty = width - filled

    return BAR_CHARS[3] * filled + BAR_CHARS[0] * empty


def ascii_scatter(
    points: list[tuple[float, float, str]],
    width: int = 50,
    height: int = 15,
    x_label: str = "X",
    y_label: str = "Y",
) -> str:
    """
    Render an ASCII scatter plot.

    Args:
        points: List of (x, y, label) tuples
        width: Plot width in characters
        height: Plot height in lines
        x_label: Label for X axis
        y_label: Label for Y axis

    Returns:
        Multiline string with the scatter plot

    Example output:
        ROE %
         40 │                    •NVDA
         20 │   •IBM    •MSFT
          0 └────────────────── P/E
            5        15       25
    """
    if not points:
        return f"[dim]No data points to plot[/]"

    # Filter out None values
    valid_points = [(x, y, label) for x, y, label in points if x is not None and y is not None]
    if not valid_points:
        return f"[dim]No valid data points[/]"

    # Calculate ranges
    x_vals = [p[0] for p in valid_points]
    y_vals = [p[1] for p in valid_points]

    x_min, x_max = min(x_vals), max(x_vals)
    y_min, y_max = min(y_vals), max(y_vals)

    # Handle edge case of same values
    x_range = x_max - x_min if x_max != x_min else 1
    y_range = y_max - y_min if y_max != y_min else 1

    # Create empty grid
    grid = [[" " for _ in range(width)] for _ in range(height)]
    labels_placed = []

    # Plot points
    for x, y, label in valid_points:
        # Normalize to grid coordinates
        grid_x = int((x - x_min) / x_range * (width - 1))
        grid_y = int((y - y_min) / y_range * (height - 1))
        grid_y = height - 1 - grid_y  # Flip Y axis

        # Clamp to grid bounds
        grid_x = max(0, min(width - 1, grid_x))
        grid_y = max(0, min(height - 1, grid_y))

        # Place point marker
        if grid[grid_y][grid_x] == " ":
            grid[grid_y][grid_x] = "•"
            # Try to place label for notable points (corners/edges)
            if len(labels_placed) < 8:
                labels_placed.append((grid_x, grid_y, label[:6]))

    # Add labels to grid (short ticker names)
    for gx, gy, lbl in labels_placed:
        # Place label to the right of point if space allows
        start = gx + 1
        if start + len(lbl) < width:
            for i, ch in enumerate(lbl):
                if grid[gy][start + i] == " ":
                    grid[gy][start + i] = ch

    # Build output lines
    lines = []

    # Y-axis label
    lines.append(f"  {y_label}")

    # Calculate Y-axis tick values
    y_ticks = [y_max, (y_max + y_min) / 2, y_min]

    # Grid rows with Y-axis
    for i, row in enumerate(grid):
        # Y-axis value (show for top, middle, bottom)
        if i == 0:
            y_tick = f"{y_max:>5.0f}"
        elif i == height // 2:
            y_tick = f"{(y_max + y_min) / 2:>5.0f}"
        elif i == height - 1:
            y_tick = f"{y_min:>5.0f}"
        else:
            y_tick = "     "

        lines.append(f"{y_tick} │{''.join(row)}")

    # X-axis
    lines.append("      └" + "─" * width)

    # X-axis labels
    x_mid = (x_max + x_min) / 2
    x_axis_labels = f"      {x_min:<.0f}" + " " * (width // 2 - 8) + f"{x_mid:.0f}" + " " * (width // 2 - 8) + f"{x_max:>.0f}"
    lines.append(x_axis_labels)
    lines.append(f"      {' ' * (width // 2 - len(x_label) // 2)}{x_label}")

    return "\n".join(lines)
