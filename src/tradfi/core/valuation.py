"""Fair value calculation methods."""

from __future__ import annotations

import math


def calculate_graham_number(eps: float | None, book_value: float | None) -> float | None:
    """
    Calculate Graham Number (Benjamin Graham's intrinsic value formula).

    Graham Number = sqrt(22.5 * EPS * Book Value per Share)

    This formula assumes a P/E of 15 and P/B of 1.5 are fair values,
    and 15 * 1.5 = 22.5

    Args:
        eps: Earnings per share (trailing)
        book_value: Book value per share

    Returns:
        Graham Number (fair value estimate) or None if inputs invalid
    """
    if eps is None or book_value is None:
        return None

    # Both EPS and book value should be positive for Graham Number to be meaningful
    if eps <= 0 or book_value <= 0:
        return None

    return math.sqrt(22.5 * eps * book_value)


def calculate_margin_of_safety(
    current_price: float, fair_value: float | None
) -> float | None:
    """
    Calculate margin of safety percentage.

    Positive = undervalued (price below fair value)
    Negative = overvalued (price above fair value)

    Args:
        current_price: Current stock price
        fair_value: Estimated fair value

    Returns:
        Margin of safety as percentage
    """
    if fair_value is None or current_price <= 0:
        return None

    return ((fair_value - current_price) / current_price) * 100


def calculate_pe_fair_value(eps: float | None, target_pe: float = 15) -> float | None:
    """
    Calculate fair value based on target P/E ratio.

    Args:
        eps: Earnings per share
        target_pe: Target P/E ratio (default 15, Graham's standard)

    Returns:
        Fair value estimate
    """
    if eps is None or eps <= 0:
        return None

    return eps * target_pe


def calculate_dcf_fair_value(
    free_cash_flow: float | None,
    shares_outstanding: float | None,
    growth_rate: float = 0.05,
    discount_rate: float = 0.10,
    terminal_growth: float = 0.03,
    years: int = 10,
) -> float | None:
    """
    Calculate fair value using simplified Discounted Cash Flow model.

    This is a two-stage DCF:
    1. Project FCF for N years at growth_rate
    2. Calculate terminal value using perpetuity growth model
    3. Discount all cash flows to present value

    Args:
        free_cash_flow: Current free cash flow (total, not per share)
        shares_outstanding: Number of shares outstanding
        growth_rate: Expected FCF growth rate (default 5%)
        discount_rate: Required rate of return / WACC (default 10%)
        terminal_growth: Perpetual growth rate after projection period (default 3%)
        years: Number of years to project (default 10)

    Returns:
        Fair value per share, or None if inputs invalid
    """
    if free_cash_flow is None or shares_outstanding is None:
        return None

    if free_cash_flow <= 0 or shares_outstanding <= 0:
        return None

    if discount_rate <= terminal_growth:
        return None  # Invalid: would result in infinite value

    # Project future cash flows
    present_value_fcf = 0.0
    projected_fcf = free_cash_flow

    for year in range(1, years + 1):
        projected_fcf *= (1 + growth_rate)
        discount_factor = (1 + discount_rate) ** year
        present_value_fcf += projected_fcf / discount_factor

    # Terminal value (Gordon Growth Model)
    terminal_fcf = projected_fcf * (1 + terminal_growth)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth)

    # Discount terminal value to present
    terminal_discount_factor = (1 + discount_rate) ** years
    present_value_terminal = terminal_value / terminal_discount_factor

    # Total enterprise value
    total_value = present_value_fcf + present_value_terminal

    # Per share value
    fair_value_per_share = total_value / shares_outstanding

    return fair_value_per_share


def calculate_earnings_power_value(
    operating_income: float | None,
    shares_outstanding: float | None,
    tax_rate: float = 0.21,
    cost_of_capital: float = 0.10,
) -> float | None:
    """
    Calculate Earnings Power Value (EPV) - Bruce Greenwald's method.

    EPV = (Operating Income * (1 - Tax Rate)) / Cost of Capital

    This assumes no growth and values the company based on current
    normalized earnings power.

    Args:
        operating_income: Operating income (EBIT)
        shares_outstanding: Number of shares outstanding
        tax_rate: Corporate tax rate (default 21%)
        cost_of_capital: WACC or required return (default 10%)

    Returns:
        Fair value per share, or None if inputs invalid
    """
    if operating_income is None or shares_outstanding is None:
        return None

    if operating_income <= 0 or shares_outstanding <= 0:
        return None

    if cost_of_capital <= 0:
        return None

    after_tax_earnings = operating_income * (1 - tax_rate)
    enterprise_value = after_tax_earnings / cost_of_capital

    return enterprise_value / shares_outstanding
