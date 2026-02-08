"""Converters between dataclasses and Pydantic schemas."""

from tradfi.api.schemas import (
    BuybackInfoSchema,
    DividendInfoSchema,
    FairValueEstimatesSchema,
    FinancialHealthSchema,
    GrowthMetricsSchema,
    ProfitabilityMetricsSchema,
    QuarterlyDataSchema,
    QuarterlyTrendsSchema,
    ScreenCriteriaSchema,
    StockSchema,
    TechnicalIndicatorsSchema,
    ValuationMetricsSchema,
)
from tradfi.core.screener import ScreenCriteria
from tradfi.models.stock import QuarterlyTrends, Stock


def stock_to_schema(stock: Stock) -> StockSchema:
    """Convert Stock dataclass to StockSchema."""
    return StockSchema(
        ticker=stock.ticker,
        name=stock.name,
        sector=stock.sector,
        industry=stock.industry,
        current_price=stock.current_price,
        currency=stock.currency,
        signal=stock.signal,
        valuation=ValuationMetricsSchema(
            pe_trailing=stock.valuation.pe_trailing,
            pe_forward=stock.valuation.pe_forward,
            pb_ratio=stock.valuation.pb_ratio,
            ps_ratio=stock.valuation.ps_ratio,
            peg_ratio=stock.valuation.peg_ratio,
            ev_ebitda=stock.valuation.ev_ebitda,
            market_cap=stock.valuation.market_cap,
            enterprise_value=stock.valuation.enterprise_value,
        ),
        profitability=ProfitabilityMetricsSchema(
            gross_margin=stock.profitability.gross_margin,
            operating_margin=stock.profitability.operating_margin,
            net_margin=stock.profitability.net_margin,
            roe=stock.profitability.roe,
            roa=stock.profitability.roa,
        ),
        financial_health=FinancialHealthSchema(
            current_ratio=stock.financial_health.current_ratio,
            quick_ratio=stock.financial_health.quick_ratio,
            debt_to_equity=stock.financial_health.debt_to_equity,
            debt_to_assets=stock.financial_health.debt_to_assets,
            interest_coverage=stock.financial_health.interest_coverage,
            free_cash_flow=stock.financial_health.free_cash_flow,
        ),
        growth=GrowthMetricsSchema(
            revenue_growth_yoy=stock.growth.revenue_growth_yoy,
            earnings_growth_yoy=stock.growth.earnings_growth_yoy,
            eps_growth_5y=stock.growth.eps_growth_5y,
        ),
        dividends=DividendInfoSchema(
            dividend_yield=stock.dividends.dividend_yield,
            dividend_rate=stock.dividends.dividend_rate,
            payout_ratio=stock.dividends.payout_ratio,
            ex_dividend_date=stock.dividends.ex_dividend_date,
        ),
        technical=TechnicalIndicatorsSchema(
            rsi_14=stock.technical.rsi_14,
            ma_50=stock.technical.ma_50,
            ma_200=stock.technical.ma_200,
            price_vs_ma_50_pct=stock.technical.price_vs_ma_50_pct,
            price_vs_ma_200_pct=stock.technical.price_vs_ma_200_pct,
            high_52w=stock.technical.high_52w,
            low_52w=stock.technical.low_52w,
            pct_from_52w_high=stock.technical.pct_from_52w_high,
            pct_from_52w_low=stock.technical.pct_from_52w_low,
            return_1m=stock.technical.return_1m,
            return_6m=stock.technical.return_6m,
            return_1y=stock.technical.return_1y,
            is_oversold=stock.technical.is_oversold,
            is_strongly_oversold=stock.technical.is_strongly_oversold,
        ),
        fair_value=FairValueEstimatesSchema(
            graham_number=stock.fair_value.graham_number,
            dcf_value=stock.fair_value.dcf_value,
            pe_fair_value=stock.fair_value.pe_fair_value,
            margin_of_safety_pct=stock.fair_value.margin_of_safety_pct,
        ),
        buyback=BuybackInfoSchema(
            insider_ownership_pct=stock.buyback.insider_ownership_pct,
            institutional_ownership_pct=stock.buyback.institutional_ownership_pct,
            fcf_yield_pct=stock.buyback.fcf_yield_pct,
            cash_per_share=stock.buyback.cash_per_share,
            shares_outstanding=stock.buyback.shares_outstanding,
            shares_outstanding_prior=stock.buyback.shares_outstanding_prior,
        ),
        eps=stock.eps,
        book_value_per_share=stock.book_value_per_share,
    )


def quarterly_trends_to_schema(trends: QuarterlyTrends) -> QuarterlyTrendsSchema:
    """Convert QuarterlyTrends dataclass to schema."""
    quarters = [
        QuarterlyDataSchema(
            quarter=q.quarter,
            revenue=q.revenue,
            net_income=q.net_income,
            gross_profit=q.gross_profit,
            operating_income=q.operating_income,
            gross_margin=q.gross_margin,
            operating_margin=q.operating_margin,
            net_margin=q.net_margin,
            eps=q.eps,
            free_cash_flow=q.free_cash_flow,
            pe_ratio=q.pe_ratio,
            peg_ratio=q.peg_ratio,
            book_value_per_share=q.book_value_per_share,
            pb_ratio=q.pb_ratio,
            price_at_quarter_end=q.price_at_quarter_end,
        )
        for q in trends.quarters
    ]
    return QuarterlyTrendsSchema(
        quarters=quarters,
        revenue_trend=trends.revenue_trend,
        margin_trend=trends.margin_trend,
        latest_qoq_revenue_growth=trends.latest_qoq_revenue_growth,
        latest_qoq_earnings_growth=trends.latest_qoq_earnings_growth,
    )


def schema_to_screen_criteria(schema: ScreenCriteriaSchema) -> ScreenCriteria:
    """Convert ScreenCriteriaSchema to ScreenCriteria dataclass."""
    return ScreenCriteria(
        pe_min=schema.pe_min,
        pe_max=schema.pe_max,
        pb_min=schema.pb_min,
        pb_max=schema.pb_max,
        ps_min=schema.ps_min,
        ps_max=schema.ps_max,
        peg_min=schema.peg_min,
        peg_max=schema.peg_max,
        roe_min=schema.roe_min,
        roe_max=schema.roe_max,
        roa_min=schema.roa_min,
        margin_min=schema.margin_min,
        margin_max=schema.margin_max,
        debt_equity_max=schema.debt_equity_max,
        current_ratio_min=schema.current_ratio_min,
        revenue_growth_min=schema.revenue_growth_min,
        earnings_growth_min=schema.earnings_growth_min,
        dividend_yield_min=schema.dividend_yield_min,
        market_cap_min=schema.market_cap_min,
        market_cap_max=schema.market_cap_max,
        rsi_min=schema.rsi_min,
        rsi_max=schema.rsi_max,
        near_52w_low_pct=schema.near_52w_low_pct,
        below_200ma=schema.below_200ma,
        below_50ma=schema.below_50ma,
        pct_below_200ma_min=schema.pct_below_200ma_min,
        pe_pb_product_max=schema.pe_pb_product_max,
        fcf_yield_min=schema.fcf_yield_min,
        insider_ownership_min=schema.insider_ownership_min,
        pct_from_52w_high_max=schema.pct_from_52w_high_max,
    )


def screen_criteria_to_schema(criteria: ScreenCriteria) -> ScreenCriteriaSchema:
    """Convert ScreenCriteria dataclass to schema."""
    return ScreenCriteriaSchema(
        pe_min=criteria.pe_min,
        pe_max=criteria.pe_max,
        pb_min=criteria.pb_min,
        pb_max=criteria.pb_max,
        ps_min=criteria.ps_min,
        ps_max=criteria.ps_max,
        peg_min=criteria.peg_min,
        peg_max=criteria.peg_max,
        roe_min=criteria.roe_min,
        roe_max=criteria.roe_max,
        roa_min=criteria.roa_min,
        margin_min=criteria.margin_min,
        margin_max=criteria.margin_max,
        debt_equity_max=criteria.debt_equity_max,
        current_ratio_min=criteria.current_ratio_min,
        revenue_growth_min=criteria.revenue_growth_min,
        earnings_growth_min=criteria.earnings_growth_min,
        dividend_yield_min=criteria.dividend_yield_min,
        market_cap_min=criteria.market_cap_min,
        market_cap_max=criteria.market_cap_max,
        rsi_min=criteria.rsi_min,
        rsi_max=criteria.rsi_max,
        near_52w_low_pct=criteria.near_52w_low_pct,
        below_200ma=criteria.below_200ma,
        below_50ma=criteria.below_50ma,
        pct_below_200ma_min=criteria.pct_below_200ma_min,
        pe_pb_product_max=criteria.pe_pb_product_max,
        fcf_yield_min=criteria.fcf_yield_min,
        insider_ownership_min=criteria.insider_ownership_min,
        pct_from_52w_high_max=criteria.pct_from_52w_high_max,
    )
