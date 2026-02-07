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


def calculate_margin_of_safety(current_price: float, fair_value: float | None) -> float | None:
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
        projected_fcf *= 1 + growth_rate
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
    Calculate Earnings Power Value (Bruce Greenwald's method).

    EPV = (Operating Income * (1 - tax_rate)) / cost_of_capital / shares_outstanding

    Assumes no growth — values the company based on current sustainable earnings.

    Args:
        operating_income: Total operating income (EBIT)
        shares_outstanding: Number of shares outstanding
        tax_rate: Effective tax rate (default 21%)
        cost_of_capital: Required rate of return / WACC (default 10%)

    Returns:
        EPV per share, or None if inputs invalid
    """
    if operating_income is None or shares_outstanding is None:
        return None

    if operating_income <= 0 or shares_outstanding <= 0:
        return None

    if cost_of_capital <= 0:
        return None

    after_tax_earnings = operating_income * (1 - tax_rate)
    epv = after_tax_earnings / cost_of_capital
    return epv / shares_outstanding


def calculate_piotroski_f_score(
    net_income: float | None,
    operating_cash_flow: float | None,
    roa: float | None,
    free_cash_flow: float | None,
    debt_to_equity: float | None,
    current_ratio: float | None,
    gross_margin: float | None,
    shares_outstanding: float | None,
    shares_outstanding_prior: float | None,
) -> tuple[int, list[str], list[str]]:
    """
    Calculate simplified Piotroski F-Score (0-9).

    Returns (score, passing_criteria, failing_criteria).
    Simplified version using single-period snapshot data.
    """
    score = 0
    passing: list[str] = []
    failing: list[str] = []

    # 1. Positive net income
    if net_income is not None and net_income > 0:
        score += 1
        passing.append("Net Income +")
    else:
        failing.append("Net Income -")

    # 2. Positive operating cash flow
    if operating_cash_flow is not None and operating_cash_flow > 0:
        score += 1
        passing.append("OCF +")
    else:
        failing.append("OCF -")

    # 3. Positive ROA (proxy for increasing ROA)
    if roa is not None and roa > 0:
        score += 1
        passing.append("ROA +")
    else:
        failing.append("ROA -")

    # 4. OCF > Net Income (earnings quality / accruals)
    if (operating_cash_flow is not None and net_income is not None
            and operating_cash_flow > net_income):
        score += 1
        passing.append("OCF > NI")
    else:
        failing.append("OCF < NI")

    # 5. Low leverage: D/E < 100 (stored as percentage in yfinance)
    if debt_to_equity is not None and debt_to_equity < 100:
        score += 1
        passing.append("Low D/E")
    else:
        failing.append("High D/E")

    # 6. Current ratio > 1
    if current_ratio is not None and current_ratio > 1:
        score += 1
        passing.append("CR > 1")
    else:
        failing.append("CR < 1")

    # 7. No dilution
    if (shares_outstanding is not None and shares_outstanding_prior is not None
            and shares_outstanding <= shares_outstanding_prior):
        score += 1
        passing.append("No dilution")
    elif shares_outstanding is not None and shares_outstanding_prior is None:
        score += 1
        passing.append("No dilution data")
    else:
        failing.append("Diluted")

    # 8. Positive gross margin (proxy for increasing)
    if gross_margin is not None and gross_margin > 0:
        score += 1
        passing.append("GM +")
    else:
        failing.append("GM -")

    # 9. Positive FCF (proxy for asset turnover)
    if free_cash_flow is not None and free_cash_flow > 0:
        score += 1
        passing.append("FCF +")
    else:
        failing.append("FCF -")

    return score, passing, failing


def generate_forensic_flags(
    fcf: float | None,
    ocf: float | None,
    net_income: float | None,
    debt_to_equity: float | None,
    margin_of_safety_pct: float | None,
    rsi: float | None,
    current_ratio: float | None,
    interest_coverage: float | None,
) -> tuple[list[str], list[str]]:
    """
    Generate green (positive) and red (negative) forensic flags.

    Returns (green_flags, red_flags).
    """
    green: list[str] = []
    red: list[str] = []

    # Cash flow analysis
    if fcf is not None:
        if fcf > 0:
            green.append("FCF positive")
        else:
            red.append("FCF negative")

    # Earnings quality: OCF vs NI
    if ocf is not None and net_income is not None and net_income != 0:
        ratio = ocf / net_income
        if ratio > 1.2:
            green.append("Earnings quality: HIGH")
        elif ratio > 0.8:
            green.append("Earnings quality: OK")
        else:
            red.append("Earnings quality: POOR")

    # Leverage
    if debt_to_equity is not None:
        de_ratio = debt_to_equity / 100  # stored as percentage
        if de_ratio < 0.3:
            green.append("Leverage: MINIMAL")
        elif de_ratio < 0.5:
            green.append("Leverage: LOW")
        elif de_ratio < 1.0:
            pass  # neutral, don't flag
        elif de_ratio < 2.0:
            red.append("Leverage: HIGH")
        else:
            red.append("Leverage: DANGEROUS")

    # Liquidity
    if current_ratio is not None:
        if current_ratio < 1.0:
            red.append("Liquidity risk (CR < 1)")

    # Interest coverage
    if interest_coverage is not None:
        if interest_coverage < 2.0:
            red.append("Weak interest coverage")

    # Valuation
    if margin_of_safety_pct is not None:
        if margin_of_safety_pct > 30:
            green.append(f"{margin_of_safety_pct:.0f}% below fair value")
        elif margin_of_safety_pct > 0:
            green.append(f"Modest discount ({margin_of_safety_pct:.0f}%)")
        elif margin_of_safety_pct > -20:
            red.append(f"Slightly overvalued ({abs(margin_of_safety_pct):.0f}%)")
        else:
            red.append(f"Overvalued ({abs(margin_of_safety_pct):.0f}% above fair value)")

    return green, red
