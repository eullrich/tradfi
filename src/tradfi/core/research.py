"""Deep research module - SEC filings and AI analysis."""

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Supported LLM providers
LLM_PROVIDER_ANTHROPIC = "anthropic"
LLM_PROVIDER_OPENROUTER = "openrouter"

# Default models for each provider
DEFAULT_MODELS = {
    LLM_PROVIDER_ANTHROPIC: "claude-sonnet-4-20250514",
    LLM_PROVIDER_OPENROUTER: "deepseek/deepseek-r1:free",  # Free model on OpenRouter
}

# API endpoints
API_ENDPOINTS = {
    LLM_PROVIDER_ANTHROPIC: "https://api.anthropic.com/v1/messages",
    LLM_PROVIDER_OPENROUTER: "https://openrouter.ai/api/v1/chat/completions",
}


@dataclass
class Filing:
    """Represents an SEC filing."""

    form_type: str  # 10-K, 10-Q
    filed_date: str
    accession_number: str
    primary_document: str
    filing_url: str
    content: str | None = None


@dataclass
class ResearchReport:
    """AI-generated research report from filing analysis."""

    ticker: str
    filing_type: str
    filing_date: str

    # Executive summary
    summary: str

    # Key metrics extracted
    revenue_trend: str | None = None
    margin_analysis: str | None = None
    cash_flow_health: str | None = None
    debt_situation: str | None = None

    # Qualitative insights
    management_tone: str | None = None
    risk_factors: list[str] | None = None
    growth_drivers: list[str] | None = None
    red_flags: list[str] | None = None

    # Overall assessment
    health_score: str | None = None  # Strong, Moderate, Weak, Concerning
    key_takeaways: list[str] | None = None


# SEC EDGAR API headers (required by SEC)
SEC_HEADERS = {
    "User-Agent": "TradFi Research Tool contact@example.com",
    "Accept-Encoding": "gzip, deflate",
}


def get_cik_for_ticker(ticker: str) -> str | None:
    """
    Get the CIK (Central Index Key) for a ticker symbol.

    Args:
        ticker: Stock ticker symbol

    Returns:
        CIK as zero-padded string, or None if not found
    """
    url = "https://www.sec.gov/files/company_tickers.json"

    try:
        req = Request(url, headers=SEC_HEADERS)
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        # Search for ticker
        ticker_upper = ticker.upper()
        for entry in data.values():
            if entry.get("ticker") == ticker_upper:
                cik = entry.get("cik_str")
                # Zero-pad to 10 digits
                return str(cik).zfill(10)

    except (HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"Error fetching CIK: {e}")

    return None


def get_recent_filings(cik: str, form_type: str = "10-K", count: int = 5) -> list[Filing]:
    """
    Get recent filings for a company.

    Args:
        cik: Zero-padded CIK
        form_type: Type of filing (10-K, 10-Q)
        count: Number of filings to return

    Returns:
        List of Filing objects
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"

    try:
        req = Request(url, headers=SEC_HEADERS)
        with urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        filings = []
        recent = data.get("filings", {}).get("recent", {})

        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        for i, form in enumerate(forms):
            if form == form_type and len(filings) < count:
                accession = accessions[i].replace("-", "")
                filings.append(Filing(
                    form_type=form,
                    filed_date=dates[i],
                    accession_number=accessions[i],
                    primary_document=primary_docs[i],
                    filing_url=f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession}/{primary_docs[i]}",
                ))

        return filings

    except (HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"Error fetching filings: {e}")
        return []


def fetch_filing_content(filing: Filing, max_chars: int = 100000) -> str | None:
    """
    Fetch the content of a filing.

    Args:
        filing: Filing object
        max_chars: Maximum characters to return (filings can be huge)

    Returns:
        Filing content as text, or None on error
    """
    try:
        req = Request(filing.filing_url, headers=SEC_HEADERS)
        with urlopen(req, timeout=30) as response:
            content = response.read().decode("utf-8", errors="ignore")

        # Strip HTML tags for cleaner text
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<[^>]+>', ' ', content)
        content = re.sub(r'&nbsp;', ' ', content)
        content = re.sub(r'&[a-zA-Z]+;', '', content)
        content = re.sub(r'\s+', ' ', content)

        # Truncate if too long
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n[TRUNCATED - Filing continues...]"

        return content.strip()

    except (HTTPError, URLError) as e:
        print(f"Error fetching filing content: {e}")
        return None


def _detect_provider() -> tuple[str, str]:
    """
    Detect which LLM provider to use based on available API keys.

    Returns:
        Tuple of (provider_name, api_key)
    """
    # Check OpenRouter first (preferred for free access)
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        return LLM_PROVIDER_OPENROUTER, openrouter_key

    # Fall back to Anthropic
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        return LLM_PROVIDER_ANTHROPIC, anthropic_key

    return "", ""


def _call_anthropic(api_key: str, model: str, prompt: str) -> str | None:
    """Call Anthropic API and return response text."""
    import urllib.request

    request_data = json.dumps({
        "model": model,
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        API_ENDPOINTS[LLM_PROVIDER_ANTHROPIC],
        data=request_data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    with urlopen(req, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))

    return result.get("content", [{}])[0].get("text", "")


def _call_openrouter(api_key: str, model: str, prompt: str) -> str | None:
    """Call OpenRouter API and return response text."""
    import urllib.request

    request_data = json.dumps({
        "model": model,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        API_ENDPOINTS[LLM_PROVIDER_OPENROUTER],
        data=request_data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/tradfi",  # Required by OpenRouter
            "X-Title": "TradFi Research Tool",
        },
        method="POST",
    )

    with urlopen(req, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))

    # OpenRouter uses OpenAI-compatible format
    choices = result.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "")
    return None


def analyze_filing_with_claude(
    ticker: str,
    filing: Filing,
    content: str,
    api_key: str | None = None,
) -> ResearchReport | None:
    """
    Analyze a filing using LLM API (Anthropic or OpenRouter).

    Args:
        ticker: Stock ticker
        filing: Filing metadata
        content: Filing text content
        api_key: API key (optional, auto-detects from env vars)

    Returns:
        ResearchReport with analysis, or None on error

    Environment variables checked (in order):
        - OPENROUTER_API_KEY: Use OpenRouter with free models
        - ANTHROPIC_API_KEY: Use Anthropic Claude directly
    """
    # Auto-detect provider if no key provided
    if api_key:
        # If key provided, try to guess provider from key format
        if api_key.startswith("sk-or-"):
            provider = LLM_PROVIDER_OPENROUTER
        else:
            provider = LLM_PROVIDER_ANTHROPIC
    else:
        provider, api_key = _detect_provider()

    if not api_key:
        return None

    model = DEFAULT_MODELS[provider]

    prompt = f"""Analyze this SEC {filing.form_type} filing for {ticker} filed on {filing.filed_date}.

Provide a deep value investor's analysis focusing on:

1. **Executive Summary** (2-3 sentences on overall company health)

2. **Financial Trends**:
   - Revenue trend (growing, stable, declining)
   - Margin analysis (improving, stable, deteriorating)
   - Cash flow health (strong, adequate, weak)
   - Debt situation (low leverage, moderate, high, concerning)

3. **Qualitative Insights**:
   - Management tone (confident, cautious, defensive, concerning)
   - Top 3 risk factors mentioned
   - Key growth drivers identified
   - Any red flags or warning signs

4. **Health Score**: Rate as Strong, Moderate, Weak, or Concerning

5. **Key Takeaways**: 3-5 bullet points a value investor should know

Format your response as JSON with this structure:
{{
  "summary": "...",
  "revenue_trend": "...",
  "margin_analysis": "...",
  "cash_flow_health": "...",
  "debt_situation": "...",
  "management_tone": "...",
  "risk_factors": ["...", "...", "..."],
  "growth_drivers": ["...", "..."],
  "red_flags": ["..."] or [],
  "health_score": "Strong|Moderate|Weak|Concerning",
  "key_takeaways": ["...", "...", "..."]
}}

FILING CONTENT:
{content[:80000]}
"""

    try:
        # Call appropriate provider
        if provider == LLM_PROVIDER_OPENROUTER:
            response_text = _call_openrouter(api_key, model, prompt)
        else:
            response_text = _call_anthropic(api_key, model, prompt)

        if not response_text:
            return None

        # Parse JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            analysis = json.loads(json_match.group())

            return ResearchReport(
                ticker=ticker,
                filing_type=filing.form_type,
                filing_date=filing.filed_date,
                summary=analysis.get("summary", ""),
                revenue_trend=analysis.get("revenue_trend"),
                margin_analysis=analysis.get("margin_analysis"),
                cash_flow_health=analysis.get("cash_flow_health"),
                debt_situation=analysis.get("debt_situation"),
                management_tone=analysis.get("management_tone"),
                risk_factors=analysis.get("risk_factors"),
                growth_drivers=analysis.get("growth_drivers"),
                red_flags=analysis.get("red_flags"),
                health_score=analysis.get("health_score"),
                key_takeaways=analysis.get("key_takeaways"),
            )

    except Exception as e:
        print(f"Error analyzing with {provider}: {e}")

    return None


def deep_research(ticker: str, api_key: str | None = None) -> ResearchReport | None:
    """
    Perform deep research on a stock by analyzing its latest SEC filing.

    Args:
        ticker: Stock ticker symbol
        api_key: Anthropic API key (optional, uses env var if not provided)

    Returns:
        ResearchReport with analysis, or None on error
    """
    # Get CIK
    cik = get_cik_for_ticker(ticker)
    if not cik:
        return None

    # Try 10-K first, then 10-Q
    filings = get_recent_filings(cik, "10-K", count=1)
    if not filings:
        filings = get_recent_filings(cik, "10-Q", count=1)

    if not filings:
        return None

    filing = filings[0]

    # Fetch content
    content = fetch_filing_content(filing)
    if not content:
        return None

    # Analyze with Claude
    return analyze_filing_with_claude(ticker, filing, content, api_key)
