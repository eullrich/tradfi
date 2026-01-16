"""Pydantic schemas for API request/response models."""

from pydantic import BaseModel, Field


class TechnicalIndicatorsSchema(BaseModel):
    """Technical/oversold indicators."""

    rsi_14: float | None = None
    ma_50: float | None = None
    ma_200: float | None = None
    price_vs_ma_50_pct: float | None = None
    price_vs_ma_200_pct: float | None = None
    high_52w: float | None = None
    low_52w: float | None = None
    pct_from_52w_high: float | None = None
    pct_from_52w_low: float | None = None
    return_1m: float | None = None
    return_6m: float | None = None
    return_1y: float | None = None
    is_oversold: bool = False
    is_strongly_oversold: bool = False


class ValuationMetricsSchema(BaseModel):
    """Valuation metrics."""

    pe_trailing: float | None = None
    pe_forward: float | None = None
    pb_ratio: float | None = None
    ps_ratio: float | None = None
    peg_ratio: float | None = None
    ev_ebitda: float | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None


class ProfitabilityMetricsSchema(BaseModel):
    """Profitability metrics."""

    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    roe: float | None = None
    roa: float | None = None


class FinancialHealthSchema(BaseModel):
    """Financial health metrics."""

    current_ratio: float | None = None
    quick_ratio: float | None = None
    debt_to_equity: float | None = None
    debt_to_assets: float | None = None
    interest_coverage: float | None = None
    free_cash_flow: float | None = None


class GrowthMetricsSchema(BaseModel):
    """Growth metrics."""

    revenue_growth_yoy: float | None = None
    earnings_growth_yoy: float | None = None
    eps_growth_5y: float | None = None


class DividendInfoSchema(BaseModel):
    """Dividend information."""

    dividend_yield: float | None = None
    dividend_rate: float | None = None
    payout_ratio: float | None = None
    ex_dividend_date: str | None = None


class FairValueEstimatesSchema(BaseModel):
    """Fair value estimates."""

    graham_number: float | None = None
    dcf_value: float | None = None
    pe_fair_value: float | None = None
    margin_of_safety_pct: float | None = None


class BuybackInfoSchema(BaseModel):
    """Buyback-related metrics."""

    insider_ownership_pct: float | None = None
    institutional_ownership_pct: float | None = None
    fcf_yield_pct: float | None = None
    cash_per_share: float | None = None
    shares_outstanding: float | None = None
    shares_outstanding_prior: float | None = None


class StockSchema(BaseModel):
    """Complete stock data model."""

    ticker: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    current_price: float | None = None
    currency: str = "USD"
    signal: str = "NO_SIGNAL"

    valuation: ValuationMetricsSchema = Field(default_factory=ValuationMetricsSchema)
    profitability: ProfitabilityMetricsSchema = Field(default_factory=ProfitabilityMetricsSchema)
    financial_health: FinancialHealthSchema = Field(default_factory=FinancialHealthSchema)
    growth: GrowthMetricsSchema = Field(default_factory=GrowthMetricsSchema)
    dividends: DividendInfoSchema = Field(default_factory=DividendInfoSchema)
    technical: TechnicalIndicatorsSchema = Field(default_factory=TechnicalIndicatorsSchema)
    fair_value: FairValueEstimatesSchema = Field(default_factory=FairValueEstimatesSchema)
    buyback: BuybackInfoSchema = Field(default_factory=BuybackInfoSchema)

    eps: float | None = None
    book_value_per_share: float | None = None


class QuarterlyDataSchema(BaseModel):
    """Single quarter of financial data."""

    quarter: str
    revenue: float | None = None
    net_income: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    eps: float | None = None
    free_cash_flow: float | None = None


class QuarterlyTrendsSchema(BaseModel):
    """Quarterly trends container."""

    quarters: list[QuarterlyDataSchema] = Field(default_factory=list)
    revenue_trend: str = "N/A"
    margin_trend: str = "N/A"
    latest_qoq_revenue_growth: float | None = None
    latest_qoq_earnings_growth: float | None = None


# Request schemas


class ScreenCriteriaSchema(BaseModel):
    """Screening criteria for filtering stocks."""

    # Valuation filters
    pe_min: float | None = None
    pe_max: float | None = None
    pb_min: float | None = None
    pb_max: float | None = None
    ps_min: float | None = None
    ps_max: float | None = None
    peg_min: float | None = None
    peg_max: float | None = None

    # Profitability filters
    roe_min: float | None = None
    roe_max: float | None = None
    roa_min: float | None = None
    margin_min: float | None = None
    margin_max: float | None = None

    # Financial health filters
    debt_equity_max: float | None = None
    current_ratio_min: float | None = None

    # Growth filters
    revenue_growth_min: float | None = None
    earnings_growth_min: float | None = None

    # Dividend filters
    dividend_yield_min: float | None = None

    # Size filters
    market_cap_min: float | None = None
    market_cap_max: float | None = None

    # Technical / Oversold filters
    rsi_min: float | None = None
    rsi_max: float | None = None
    near_52w_low_pct: float | None = None
    below_200ma: bool = False
    below_50ma: bool = False
    pct_below_200ma_min: float | None = None

    # Graham special criteria
    pe_pb_product_max: float | None = None

    # Buyback potential criteria
    fcf_yield_min: float | None = None
    insider_ownership_min: float | None = None
    pct_from_52w_high_max: float | None = None


class ScreenRequestSchema(BaseModel):
    """Request body for screening endpoint."""

    universe: str = "sp500"
    preset: str | None = None
    criteria: ScreenCriteriaSchema | None = None
    limit: int = Field(default=50, ge=1, le=500)


class AnalyzeRequestSchema(BaseModel):
    """Request body for multi-stock analysis."""

    tickers: list[str] = Field(..., min_length=1, max_length=50)


# List management schemas


class CreateListSchema(BaseModel):
    """Request body for creating a list."""

    name: str = Field(..., min_length=1, max_length=50)
    tickers: list[str] = Field(default_factory=list)


class AddTickerSchema(BaseModel):
    """Request body for adding a ticker to a list."""

    ticker: str


class ListNoteSchema(BaseModel):
    """Request body for adding notes to a list item."""

    notes: str | None = None
    thesis: str | None = None
    entry_price: float | None = None
    target_price: float | None = None


class ListItemSchema(BaseModel):
    """List item with optional notes."""

    ticker: str
    notes: str | None = None
    thesis: str | None = None
    entry_price: float | None = None
    target_price: float | None = None


class SavedListSchema(BaseModel):
    """Saved list response."""

    name: str
    tickers: list[str]
    items: list[ListItemSchema] = Field(default_factory=list)
    created_at: str | None = None


class CategorySchema(BaseModel):
    """Category schema."""

    id: int | None = None
    name: str
    icon: str | None = None


class CreateCategorySchema(BaseModel):
    """Request body for creating a category."""

    name: str = Field(..., min_length=1, max_length=50)
    icon: str | None = None


# Watchlist schemas


class WatchlistItemSchema(BaseModel):
    """Watchlist item."""

    ticker: str
    added_at: str | None = None
    notes: str | None = None


class WatchlistNoteSchema(BaseModel):
    """Request body for updating watchlist notes."""

    notes: str


# Universe schemas


class UniverseSchema(BaseModel):
    """Universe information."""

    name: str
    description: str
    count: int


class PresetSchema(BaseModel):
    """Preset screen information."""

    name: str
    criteria: ScreenCriteriaSchema


# Response schemas


class ScreenResultSchema(BaseModel):
    """Screening result response."""

    universe: str
    preset: str | None = None
    total_screened: int
    matches: int
    stocks: list[StockSchema]


class CacheStatsSchema(BaseModel):
    """Cache statistics."""

    total: int
    fresh: int
    stale: int


class MessageSchema(BaseModel):
    """Generic message response."""

    message: str


class ErrorSchema(BaseModel):
    """Error response."""

    detail: str
