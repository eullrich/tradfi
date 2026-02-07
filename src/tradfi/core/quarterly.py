"""Quarterly financial data fetching and analysis."""

from typing import Optional

import pandas as pd
import yfinance as yf

from tradfi.models.stock import QuarterlyData, QuarterlyTrends


def fetch_quarterly_financials(ticker_symbol: str, periods: int = 8) -> Optional[QuarterlyTrends]:
    """
    Fetch quarterly financial data from yfinance.

    Args:
        ticker_symbol: Stock ticker (e.g., "AAPL")
        periods: Number of quarters to fetch (default 8)

    Returns:
        QuarterlyTrends object with quarterly data, or None if fetch failed
    """
    try:
        ticker = yf.Ticker(ticker_symbol.upper())

        # Get quarterly financial statements
        # yfinance returns these as DataFrames with dates as columns
        income_stmt = ticker.quarterly_income_stmt
        _balance_sheet = ticker.quarterly_balance_sheet
        cashflow = ticker.quarterly_cashflow

        if income_stmt is None or income_stmt.empty:
            return None

        quarters = []

        # Get column dates (quarters) - most recent first
        dates = income_stmt.columns[:periods]

        for date in dates:
            # Extract quarter string from date
            quarter_str = _date_to_quarter(date)

            # Get values from income statement
            revenue = _safe_get(income_stmt, "Total Revenue", date)
            gross_profit = _safe_get(income_stmt, "Gross Profit", date)
            operating_income = _safe_get(income_stmt, "Operating Income", date)
            net_income = _safe_get(income_stmt, "Net Income", date)

            # Calculate margins
            gross_margin = None
            operating_margin = None
            net_margin = None

            if revenue and revenue != 0:
                if gross_profit is not None:
                    gross_margin = (gross_profit / revenue) * 100
                if operating_income is not None:
                    operating_margin = (operating_income / revenue) * 100
                if net_income is not None:
                    net_margin = (net_income / revenue) * 100

            # Get EPS if available
            eps = _safe_get(income_stmt, "Basic EPS", date)
            if eps is None:
                eps = _safe_get(income_stmt, "Diluted EPS", date)

            # Get free cash flow from cash flow statement
            fcf = None
            if cashflow is not None and not cashflow.empty and date in cashflow.columns:
                operating_cf = _safe_get(cashflow, "Operating Cash Flow", date)
                capex = _safe_get(cashflow, "Capital Expenditure", date)
                if operating_cf is not None and capex is not None:
                    fcf = operating_cf + capex  # capex is negative

            quarterly_data = QuarterlyData(
                quarter=quarter_str,
                revenue=revenue,
                net_income=net_income,
                gross_profit=gross_profit,
                operating_income=operating_income,
                gross_margin=gross_margin,
                operating_margin=operating_margin,
                net_margin=net_margin,
                eps=eps,
                free_cash_flow=fcf,
            )
            quarters.append(quarterly_data)

        return QuarterlyTrends(quarters=quarters)

    except Exception as e:
        print(f"Error fetching quarterly data for {ticker_symbol}: {e}")
        return None


def _date_to_quarter(date) -> str:
    """Convert a pandas Timestamp to quarter string like '2024Q3'."""
    if hasattr(date, "year") and hasattr(date, "quarter"):
        return f"{date.year}Q{date.quarter}"
    elif hasattr(date, "year") and hasattr(date, "month"):
        quarter = (date.month - 1) // 3 + 1
        return f"{date.year}Q{quarter}"
    else:
        return str(date)


def _safe_get(df: pd.DataFrame, row_name: str, col) -> Optional[float]:
    """Safely get a value from a DataFrame, handling missing data."""
    try:
        if row_name in df.index and col in df.columns:
            value = df.loc[row_name, col]
            if pd.notna(value):
                return float(value)
    except (KeyError, TypeError, ValueError):
        pass
    return None


def calculate_qoq_growth(quarters: list[QuarterlyData], metric: str) -> list[Optional[float]]:
    """
    Calculate quarter-over-quarter growth rates for a metric.

    Args:
        quarters: List of QuarterlyData objects (most recent first)
        metric: Attribute name to calculate growth for (e.g., 'revenue')

    Returns:
        List of growth percentages (None for first quarter or missing data)
    """
    growth_rates = [None]  # First quarter has no prior to compare

    for i in range(1, len(quarters)):
        current = getattr(quarters[i - 1], metric, None)
        prior = getattr(quarters[i], metric, None)

        if current is not None and prior is not None and prior != 0:
            growth = ((current - prior) / abs(prior)) * 100
            growth_rates.append(growth)
        else:
            growth_rates.append(None)

    return growth_rates


def get_quarterly_summary(trends: QuarterlyTrends) -> dict:
    """
    Generate a summary of quarterly trends.

    Returns:
        Dictionary with trend summaries and key metrics
    """
    if not trends or not trends.quarters:
        return {"error": "No quarterly data available"}

    latest = trends.quarters[0]

    return {
        "latest_quarter": latest.quarter,
        "revenue": latest.revenue,
        "net_income": latest.net_income,
        "gross_margin": latest.gross_margin,
        "operating_margin": latest.operating_margin,
        "net_margin": latest.net_margin,
        "revenue_trend": trends.revenue_trend,
        "margin_trend": trends.margin_trend,
        "qoq_revenue_growth": trends.latest_qoq_revenue_growth,
        "qoq_earnings_growth": trends.latest_qoq_earnings_growth,
        "quarters_available": len(trends.quarters),
    }
