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
        balance_sheet = ticker.quarterly_balance_sheet
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

            # Get book value per share from balance sheet
            book_value_per_share = None
            if (
                balance_sheet is not None
                and not balance_sheet.empty
                and date in balance_sheet.columns
            ):
                stockholders_equity = _safe_get(balance_sheet, "Stockholders Equity", date)
                if stockholders_equity is None:
                    stockholders_equity = _safe_get(
                        balance_sheet, "Total Equity Gross Minority Interest", date
                    )
                shares = _safe_get(balance_sheet, "Ordinary Shares Number", date)
                if shares is None:
                    shares = _safe_get(balance_sheet, "Share Issued", date)
                if stockholders_equity is not None and shares is not None and shares > 0:
                    book_value_per_share = stockholders_equity / shares

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
                book_value_per_share=book_value_per_share,
            )
            quarters.append(quarterly_data)

        # Compute trailing P/E and PEG per quarter
        # Fetch 2Y of historical prices for quarter-end lookups
        try:
            ticker_obj = yf.Ticker(ticker_symbol.upper())
            price_history = ticker_obj.history(period="2y")
            if not price_history.empty:
                close_prices = price_history["Close"]

                for i, q in enumerate(quarters):
                    # Get quarter-end date approximation from quarter string (e.g., "2024Q3")
                    year = int(q.quarter[:4])
                    qtr = int(q.quarter[-1])
                    # Quarter end months: Q1=Mar, Q2=Jun, Q3=Sep, Q4=Dec
                    end_month = qtr * 3
                    quarter_end = f"{year}-{end_month:02d}"

                    # Find closest price to quarter end
                    try:
                        # Get prices for that month
                        month_prices = close_prices[
                            close_prices.index.strftime("%Y-%m") == quarter_end
                        ]
                        if not month_prices.empty:
                            price_at_qend = float(month_prices.iloc[-1])
                        else:
                            continue
                    except (IndexError, KeyError):
                        continue

                    # Always store the quarter-end price
                    q.price_at_quarter_end = price_at_qend

                    # Compute P/B ratio (independent of trailing EPS)
                    if q.book_value_per_share is not None and q.book_value_per_share > 0:
                        q.pb_ratio = round(price_at_qend / q.book_value_per_share, 2)

                    # Compute trailing 4Q EPS (sum of this quarter + prior 3)
                    eps_values = []
                    for j in range(i, min(i + 4, len(quarters))):
                        if quarters[j].eps is not None:
                            eps_values.append(quarters[j].eps)

                    if len(eps_values) == 4:
                        trailing_eps = sum(eps_values)
                        if trailing_eps > 0:
                            q.pe_ratio = round(price_at_qend / trailing_eps, 2)

                            # Compute YoY EPS growth for PEG
                            # Need trailing EPS from 4 quarters ago
                            yoy_eps_values = []
                            for j in range(i + 4, min(i + 8, len(quarters))):
                                if quarters[j].eps is not None:
                                    yoy_eps_values.append(quarters[j].eps)

                            if len(yoy_eps_values) == 4:
                                prior_trailing_eps = sum(yoy_eps_values)
                                if prior_trailing_eps > 0:
                                    eps_growth = (
                                        (trailing_eps - prior_trailing_eps)
                                        / abs(prior_trailing_eps)
                                    ) * 100
                                    if eps_growth > 0:
                                        q.peg_ratio = round(q.pe_ratio / eps_growth, 2)
        except Exception:
            pass  # P/E and PEG are nice-to-have, don't fail on them

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
