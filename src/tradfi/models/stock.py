"""Stock data models."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QuarterlyData:
    """Single quarter of financial data for trend analysis."""

    quarter: str  # Format: "2024Q3"
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    gross_margin: Optional[float] = None  # As percentage
    operating_margin: Optional[float] = None  # As percentage
    net_margin: Optional[float] = None  # As percentage
    eps: Optional[float] = None
    free_cash_flow: Optional[float] = None
    pe_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None
    book_value_per_share: Optional[float] = None
    pb_ratio: Optional[float] = None
    price_at_quarter_end: Optional[float] = None
    market_cap: Optional[float] = None


@dataclass
class QuarterlyTrends:
    """Container for multiple quarters of data with trend analysis."""

    quarters: list[QuarterlyData] = field(default_factory=list)

    @property
    def revenue_trend(self) -> str:
        """Calculate revenue trend direction based on recent quarters."""
        revenues = [q.revenue for q in self.quarters if q.revenue is not None]
        if len(revenues) < 2:
            return "N/A"

        # Compare most recent quarter to average of prior quarters
        recent = revenues[0]
        prior_avg = sum(revenues[1:4]) / len(revenues[1:4]) if len(revenues) > 1 else recent

        if prior_avg == 0:
            return "N/A"

        change_pct = ((recent - prior_avg) / abs(prior_avg)) * 100

        if change_pct > 5:
            return "Growing"
        elif change_pct < -5:
            return "Declining"
        else:
            return "Stable"

    @property
    def margin_trend(self) -> str:
        """Calculate margin trend (expanding/contracting)."""
        margins = [q.gross_margin for q in self.quarters if q.gross_margin is not None]
        if len(margins) < 2:
            return "N/A"

        # Compare most recent to average of prior quarters
        recent = margins[0]
        prior_avg = sum(margins[1:4]) / len(margins[1:4]) if len(margins) > 1 else recent

        if prior_avg == 0:
            return "N/A"

        change = recent - prior_avg

        if change > 1:  # More than 1 percentage point improvement
            return "Expanding"
        elif change < -1:
            return "Contracting"
        else:
            return "Stable"

    @property
    def latest_qoq_revenue_growth(self) -> Optional[float]:
        """Get quarter-over-quarter revenue growth for most recent quarter."""
        revenues = [q.revenue for q in self.quarters if q.revenue is not None]
        if len(revenues) < 2:
            return None
        if revenues[1] == 0:
            return None
        return ((revenues[0] - revenues[1]) / abs(revenues[1])) * 100

    @property
    def latest_qoq_earnings_growth(self) -> Optional[float]:
        """Get quarter-over-quarter net income growth for most recent quarter."""
        incomes = [q.net_income for q in self.quarters if q.net_income is not None]
        if len(incomes) < 2:
            return None
        if incomes[1] == 0:
            return None
        return ((incomes[0] - incomes[1]) / abs(incomes[1])) * 100

    def get_metric_values(self, metric: str) -> list[float]:
        """Get a list of values for a specific metric across quarters."""
        values = []
        for q in self.quarters:
            val = getattr(q, metric, None)
            if val is not None:
                values.append(val)
        return values


@dataclass
class TechnicalIndicators:
    """Technical/oversold indicators for a stock."""

    rsi_14: Optional[float] = None
    ma_50: Optional[float] = None
    ma_200: Optional[float] = None
    price_vs_ma_50_pct: Optional[float] = None
    price_vs_ma_200_pct: Optional[float] = None
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None
    pct_from_52w_high: Optional[float] = None
    pct_from_52w_low: Optional[float] = None
    return_1m: Optional[float] = None  # 1 month return %
    return_6m: Optional[float] = None  # 6 month return %
    return_1y: Optional[float] = None  # 1 year return %

    @property
    def is_oversold(self) -> bool:
        """Check if stock shows oversold signals."""
        if self.rsi_14 is not None and self.rsi_14 < 30:
            return True
        if self.pct_from_52w_low is not None and self.pct_from_52w_low < 10:
            return True
        return False

    @property
    def is_strongly_oversold(self) -> bool:
        """Check if stock shows strong oversold signals."""
        if self.rsi_14 is not None and self.rsi_14 < 20:
            return True
        return False


@dataclass
class ValuationMetrics:
    """Valuation metrics for a stock."""

    pe_trailing: Optional[float] = None
    pe_forward: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None


@dataclass
class ProfitabilityMetrics:
    """Profitability metrics for a stock."""

    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None


@dataclass
class FinancialHealth:
    """Financial health metrics for a stock."""

    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    debt_to_assets: Optional[float] = None
    interest_coverage: Optional[float] = None
    free_cash_flow: Optional[float] = None
    operating_cash_flow: Optional[float] = None    # yfinance: operatingCashflow
    total_debt: Optional[float] = None             # yfinance: totalDebt
    total_cash: Optional[float] = None             # yfinance: totalCash
    net_income: Optional[float] = None             # yfinance: netIncomeToCommon
    ebitda: Optional[float] = None                 # yfinance: ebitda


@dataclass
class GrowthMetrics:
    """Growth metrics for a stock."""

    revenue_growth_yoy: Optional[float] = None
    earnings_growth_yoy: Optional[float] = None
    eps_growth_5y: Optional[float] = None


@dataclass
class DividendInfo:
    """Dividend information for a stock."""

    dividend_yield: Optional[float] = None  # As percentage (e.g., 3.5 for 3.5%)
    dividend_rate: Optional[float] = None  # Annual dividend per share
    payout_ratio: Optional[float] = None  # As percentage
    ex_dividend_date: Optional[str] = None
    dividend_frequency: Optional[str] = None  # "monthly", "quarterly", "semi-annual", "annual"
    trailing_annual_dividend_rate: Optional[float] = None  # Trailing 12-month dividend per share
    five_year_avg_dividend_yield: Optional[float] = None  # 5-year average yield (as percentage)
    last_dividend_value: Optional[float] = None  # Most recent dividend amount
    last_dividend_date: Optional[str] = None  # Most recent payment date


@dataclass
class FairValueEstimates:
    """Fair value estimates from various methods."""

    graham_number: Optional[float] = None
    dcf_value: Optional[float] = None
    pe_fair_value: Optional[float] = None  # Based on P/E of 15
    epv_value: Optional[float] = None  # Earnings Power Value
    margin_of_safety_pct: Optional[float] = None  # Based on best available estimate


@dataclass
class BuybackInfo:
    """Buyback-related metrics for a stock."""

    insider_ownership_pct: Optional[float] = None  # % held by insiders
    institutional_ownership_pct: Optional[float] = None  # % held by institutions
    fcf_yield_pct: Optional[float] = None  # Free cash flow / market cap
    cash_per_share: Optional[float] = None  # Total cash per share
    shares_outstanding: Optional[float] = None
    shares_outstanding_prior: Optional[float] = None  # For detecting buybacks


@dataclass
class ETFMetrics:
    """ETF-specific metrics."""

    expense_ratio: Optional[float] = None  # As percentage (e.g., 0.03 for 0.03%)
    aum: Optional[float] = None  # Assets under management (total assets)
    avg_volume: Optional[float] = None  # Average daily volume
    holdings_count: Optional[int] = None  # Number of holdings in fund
    nav: Optional[float] = None  # Net asset value per share
    premium_discount: Optional[float] = None  # Premium/discount to NAV (%)
    inception_date: Optional[str] = None  # Fund inception date
    fund_family: Optional[str] = None  # Issuer (Vanguard, iShares, etc.)
    category: Optional[str] = None  # Fund category from data file
    legal_type: Optional[str] = None  # Legal structure (ETF, Open-End Fund, etc.)
    benchmark: Optional[str] = None  # Tracking index name
    ytd_return: Optional[float] = None  # Year-to-date return (%)
    return_3y: Optional[float] = None  # 3-year annualized return (%)
    return_5y: Optional[float] = None  # 5-year annualized return (%)
    beta_3y: Optional[float] = None  # 3-year beta vs market

    @property
    def is_low_cost(self) -> bool:
        """Check if ETF has low expense ratio (< 0.20%)."""
        return self.expense_ratio is not None and self.expense_ratio < 0.20

    @property
    def is_liquid(self) -> bool:
        """Check if ETF has good liquidity (AUM > $100M)."""
        return self.aum is not None and self.aum > 100_000_000


@dataclass
class Stock:
    """Complete stock/ETF data model."""

    ticker: str
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    current_price: Optional[float] = None
    currency: str = "USD"
    asset_type: str = "stock"  # "stock" or "etf"

    valuation: ValuationMetrics = field(default_factory=ValuationMetrics)
    profitability: ProfitabilityMetrics = field(default_factory=ProfitabilityMetrics)
    financial_health: FinancialHealth = field(default_factory=FinancialHealth)
    growth: GrowthMetrics = field(default_factory=GrowthMetrics)
    dividends: DividendInfo = field(default_factory=DividendInfo)
    technical: TechnicalIndicators = field(default_factory=TechnicalIndicators)
    fair_value: FairValueEstimates = field(default_factory=FairValueEstimates)
    buyback: BuybackInfo = field(default_factory=BuybackInfo)
    etf: ETFMetrics = field(default_factory=ETFMetrics)  # ETF-specific metrics

    # Raw data for calculations
    eps: Optional[float] = None
    book_value_per_share: Optional[float] = None
    shares_outstanding: Optional[float] = None
    operating_income: Optional[float] = None

    @property
    def signal(self) -> str:
        """Generate buy/watch/neutral signal based on asset type."""
        if self.asset_type == "etf":
            return self._etf_signal()
        return self._stock_signal()

    def _stock_signal(self) -> str:
        """Generate signal for stocks based on value + oversold."""
        is_value = self._is_value_stock()
        is_oversold = self.technical.is_oversold
        is_strongly_oversold = self.technical.is_strongly_oversold

        if is_value and is_strongly_oversold:
            return "STRONG_BUY"
        elif is_value and is_oversold:
            return "BUY"
        elif is_value and self._is_near_oversold():
            return "WATCH"
        elif is_value:
            return "NEUTRAL"
        else:
            return "NO_SIGNAL"

    def _etf_signal(self) -> str:
        """Generate signal for ETFs based on cost + performance + technicals."""
        is_low_cost = self.etf.is_low_cost
        is_liquid = self.etf.is_liquid
        is_oversold = self.technical.is_oversold
        is_strongly_oversold = self.technical.is_strongly_oversold

        # Low cost + liquid + strongly oversold = strong opportunity
        if is_low_cost and is_liquid and is_strongly_oversold:
            return "STRONG_BUY"
        # Low cost + oversold = opportunity
        elif is_low_cost and is_oversold:
            return "BUY"
        # Low cost + near oversold or good performance dip
        elif is_low_cost and self._is_near_oversold():
            return "WATCH"
        # Low cost fund with good liquidity
        elif is_low_cost and is_liquid:
            return "NEUTRAL"
        else:
            return "NO_SIGNAL"

    def _is_value_stock(self) -> bool:
        """Check if stock meets basic value criteria."""
        pe = self.valuation.pe_trailing
        pb = self.valuation.pb_ratio

        # Basic value check: reasonable P/E and P/B
        if pe is not None and pe > 0 and pe < 20:
            if pb is not None and pb > 0 and pb < 3:
                return True
        return False

    def _is_near_oversold(self) -> bool:
        """Check if approaching oversold territory."""
        rsi = self.technical.rsi_14
        if rsi is not None and 30 <= rsi < 40:
            return True
        pct_from_low = self.technical.pct_from_52w_low
        if pct_from_low is not None and pct_from_low < 20:
            return True
        return False
