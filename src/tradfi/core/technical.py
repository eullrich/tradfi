"""Technical indicator calculations."""

import pandas as pd


def calculate_rsi(prices: pd.Series, period: int = 14) -> float | None:
    """
    Calculate RSI (Relative Strength Index).

    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss over period

    Args:
        prices: Series of closing prices
        period: RSI period (default 14)

    Returns:
        RSI value (0-100) or None if insufficient data
    """
    if len(prices) < period + 1:
        return None

    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    # Avoid division by zero
    rs = avg_gain / avg_loss.replace(0, float("inf"))
    rsi = 100 - (100 / (1 + rs))

    result = rsi.iloc[-1]
    if pd.isna(result):
        return None
    return float(result)


def calculate_sma(prices: pd.Series, period: int) -> float | None:
    """
    Calculate Simple Moving Average.

    Args:
        prices: Series of closing prices
        period: MA period (e.g., 50 or 200)

    Returns:
        SMA value or None if insufficient data
    """
    if len(prices) < period:
        return None

    sma = prices.rolling(window=period).mean().iloc[-1]
    if pd.isna(sma):
        return None
    return float(sma)


def calculate_price_vs_ma_pct(current_price: float, ma: float | None) -> float | None:
    """
    Calculate percentage above/below a moving average.

    Args:
        current_price: Current stock price
        ma: Moving average value

    Returns:
        Percentage (positive = above MA, negative = below MA)
    """
    if ma is None or ma == 0:
        return None
    return ((current_price - ma) / ma) * 100


def calculate_52w_metrics(
    high_52w: float | None, low_52w: float | None, current_price: float
) -> dict:
    """
    Calculate 52-week high/low metrics.

    Args:
        high_52w: 52-week high price
        low_52w: 52-week low price
        current_price: Current stock price

    Returns:
        Dict with pct_from_high, pct_from_low, position_in_range
    """
    result = {
        "pct_from_high": None,
        "pct_from_low": None,
        "position_in_range": None,
    }

    if high_52w is not None and high_52w > 0:
        result["pct_from_high"] = ((current_price - high_52w) / high_52w) * 100

    if low_52w is not None and low_52w > 0:
        result["pct_from_low"] = ((current_price - low_52w) / low_52w) * 100

    if high_52w is not None and low_52w is not None and high_52w != low_52w:
        result["position_in_range"] = ((current_price - low_52w) / (high_52w - low_52w)) * 100

    return result


def interpret_rsi(rsi: float | None) -> str:
    """
    Interpret RSI value.

    Args:
        rsi: RSI value

    Returns:
        Human-readable interpretation
    """
    if rsi is None:
        return "N/A"
    if rsi < 20:
        return "STRONGLY OVERSOLD"
    if rsi < 30:
        return "OVERSOLD"
    if rsi < 40:
        return "APPROACHING OVERSOLD"
    if rsi < 60:
        return "NEUTRAL"
    if rsi < 70:
        return "APPROACHING OVERBOUGHT"
    if rsi < 80:
        return "OVERBOUGHT"
    return "STRONGLY OVERBOUGHT"
