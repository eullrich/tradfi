"""Main TUI application for tradfi."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    OptionList,
    SelectionList,
    Static,
    TabbedContent,
    TabPane,
)
from textual.worker import Worker


# Action menu categories and items
ACTION_MENU_ITEMS = {
    "Navigate": [
        ("search", "/", "Search ticker"),
        ("universe", "u", "Filter by universe"),
        ("industry", "f", "Filter by industry"),
        ("clear", "c", "Clear all filters"),
    ],
    "Sort By": [
        ("sort_pe", "6", "P/E ratio (value)"),
        ("sort_mos", "-", "Margin of Safety"),
        ("sort_rsi", "0", "RSI (oversold)"),
        ("sort_roe", "8", "ROE (quality)"),
        ("sort_div", "9", "Dividend yield"),
        ("sort_price", "2", "Price"),
        ("sort_1m", "3", "1-month return"),
        ("sort_6m", "4", "6-month return"),
        ("sort_1y", "5", "1-year return"),
        ("sort_ticker", "1", "Ticker"),
        ("sort_industry", "i", "Industry"),
        ("sort_pb", "7", "P/B ratio"),
    ],
    "Actions": [
        ("refresh", "r", "Refresh / Run screen"),
        ("save", "s", "Save current list"),
        ("clear_cache", "C", "Clear cache"),
        ("resync", "R", "Resync all universes"),
    ],
    "View": [
        ("help", "?", "Show all shortcuts"),
    ],
}


class ActionMenuScreen(ModalScreen):
    """Modal action menu for discoverable commands."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("space", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    CSS = """
    ActionMenuScreen {
        align: center middle;
    }

    #action-menu-container {
        width: 60;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #action-menu-title {
        text-align: center;
        text-style: bold;
        color: $secondary;
        padding-bottom: 1;
    }

    .action-category {
        color: $primary;
        text-style: bold;
        padding: 1 0 0 0;
    }

    .action-item {
        padding: 0 0 0 2;
    }

    .action-key {
        color: $success;
        text-style: bold;
    }

    #action-menu-footer {
        text-align: center;
        color: $text-muted;
        padding-top: 1;
        border-top: solid $primary;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="action-menu-container"):
            yield Static("[bold cyan]Actions[/]", id="action-menu-title")

            for category, items in ACTION_MENU_ITEMS.items():
                yield Static(f"[bold magenta]{category}[/]", classes="action-category")
                for action_id, key, description in items:
                    yield Static(
                        f"  [bold green]{key:>2}[/]  {description}",
                        classes="action-item"
                    )

            yield Static(
                "[dim]Press key to execute, Space/Esc to close[/]",
                id="action-menu-footer"
            )

    def on_key(self, event) -> None:
        """Handle key presses to execute actions."""
        key = event.key

        # Find matching action
        for category, items in ACTION_MENU_ITEMS.items():
            for action_id, action_key, description in items:
                if key == action_key:
                    self.dismiss(action_id)
                    return

from tradfi.core.screener import (
    AVAILABLE_UNIVERSES,
    PRESET_SCREENS,
    ScreenCriteria,
    get_universe_categories,
    load_tickers,
    load_tickers_by_categories,
    screen_stock,
)
from tradfi.models.stock import Stock
from tradfi.core.remote_provider import RemoteDataProvider


def _simplify_industry(industry: str) -> str:
    """Simplify industry name for compact display."""
    ind = industry
    ind = ind.replace("Manufacturers", "Mfr")
    ind = ind.replace("Manufacturer", "Mfr")
    ind = ind.replace(" - General", "")
    ind = ind.replace(" - Diversified", "")
    ind = ind.replace(" - Specialty", " Spec")
    ind = ind.replace("Insurance - Property & Casualty", "P&C Insurance")
    ind = ind.replace("Banks - Diversified", "Diversified Banks")
    ind = ind.replace("Drug ", "Pharma ")
    ind = ind.replace("Household & Personal Products", "Household Prod")
    ind = ind.replace("Capital Markets", "Cap Markets")
    ind = ind.replace("Telecom Services", "Telecom")
    ind = ind.replace("Entertainment", "Entertain")
    ind = ind.replace("Healthcare Plans", "Health Plans")
    ind = ind.replace("Conglomerates", "Conglom")
    if len(ind) > 16:
        ind = ind[:14] + ".."
    return ind


class StockDetailScreen(Screen):
    """Screen showing detailed stock analysis."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("w", "add_to_watchlist", "Add to Watchlist"),
        Binding("l", "add_to_long", "Add to Long"),
        Binding("x", "add_to_short", "Add to Short"),
        Binding("d", "deep_research", "Deep Research"),
        Binding("q", "quarterly_data", "Quarterly"),
    ]

    def __init__(self, stock: Stock, remote_provider: RemoteDataProvider) -> None:
        super().__init__()
        self.stock = stock
        self.remote_provider = remote_provider
        self.research_report = None
        self.quarterly_data = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static(f"[bold cyan]{self.stock.ticker}[/] - {self.stock.name or 'N/A'}", id="stock-title"),
            Static(f"[dim]{self.stock.sector or 'Unknown Sector'} | {self.stock.industry or 'Unknown Industry'}[/]", id="stock-subtitle"),
            Horizontal(
                self._create_panel("Price & Signal", self._get_price_info()),
                self._create_panel("Valuation", self._get_valuation_info()),
                self._create_panel("Profitability", self._get_profitability_info()),
                id="top-panels",
            ),
            Horizontal(
                self._create_panel("Financial Health", self._get_health_info()),
                self._create_panel("Technical", self._get_technical_info()),
                self._create_panel("Fair Value", self._get_fair_value_info()),
                id="bottom-panels",
            ),
            Horizontal(
                self._create_panel("Buyback Potential", self._get_buyback_info()),
                id="buyback-panel",
            ),
            Static("", id="quarterly-panel"),
            Static("", id="research-panel"),
            id="detail-container",
        )
        yield Footer()

    def _create_panel(self, title: str, content: str) -> Static:
        return Static(f"[bold magenta]{title}[/]\n{content}", classes="info-panel")

    def _get_price_info(self) -> str:
        s = self.stock
        price = f"${s.current_price:.2f}" if s.current_price else "N/A"
        signal = s.signal
        signal_color = {
            "STRONG_BUY": "bold green",
            "BUY": "green",
            "WATCH": "yellow",
            "NEUTRAL": "dim",
            "NO_SIGNAL": "dim",
        }.get(signal, "dim")

        # Generate narrative
        signal_desc = {
            "STRONG_BUY": "Multiple value indicators align - potentially undervalued with strong fundamentals.",
            "BUY": "Shows value characteristics worth investigating further.",
            "WATCH": "Some positive signals but doesn't meet all criteria yet.",
            "NEUTRAL": "No strong value signals detected.",
            "NO_SIGNAL": "Insufficient data to generate a signal.",
        }.get(signal, "")

        lines = [
            f"Price: [bold]{price}[/]",
            f"Signal: [{signal_color}]{signal}[/]",
            "",
            f"[dim]{signal_desc}[/]",
        ]
        return "\n".join(lines)

    def _get_valuation_info(self) -> str:
        v = self.stock.valuation

        # Color code based on value thresholds
        pe = v.pe_trailing
        pe_color = "green" if pe and pe < 15 else "yellow" if pe and pe < 25 else "red" if pe else "dim"
        pb = v.pb_ratio
        pb_color = "green" if pb and pb < 1.5 else "yellow" if pb and pb < 3 else "red" if pb else "dim"
        peg = v.peg_ratio
        peg_color = "green" if peg and peg < 1 else "yellow" if peg and peg < 2 else "red" if peg else "dim"

        lines = [
            f"P/E: [{pe_color}]{self._fmt(pe)}[/]",
            f"P/B: [{pb_color}]{self._fmt(pb)}[/]",
            f"P/S: {self._fmt(v.ps_ratio)}",
            f"PEG: [{peg_color}]{self._fmt(peg)}[/]",
            f"EV/EBITDA: {self._fmt(v.ev_ebitda)}",
            "",
            "[dim]Lower = cheaper. P/E<15 is",
            "value territory. P/B<1.5 means",
            "trading below book. PEG<1 is",
            "growth at reasonable price.[/]",
        ]
        return "\n".join(lines)

    def _get_profitability_info(self) -> str:
        p = self.stock.profitability

        # Color code based on quality thresholds
        roe = p.roe
        roe_color = "green" if roe and roe > 15 else "yellow" if roe and roe > 10 else "red" if roe else "dim"
        roa = p.roa
        roa_color = "green" if roa and roa > 10 else "yellow" if roa and roa > 5 else "red" if roa else "dim"
        margin = p.net_margin
        margin_color = "green" if margin and margin > 15 else "yellow" if margin and margin > 5 else "red" if margin else "dim"

        lines = [
            f"ROE: [{roe_color}]{self._pct(roe)}[/]",
            f"ROA: [{roa_color}]{self._pct(roa)}[/]",
            f"Net Margin: [{margin_color}]{self._pct(margin)}[/]",
            f"Gross Margin: {self._pct(p.gross_margin)}",
            "",
            "[dim]Higher = more profitable.",
            "ROE>15% is excellent. ROA>10%",
            "shows efficient asset use.",
            "Net margin>15% is strong.[/]",
        ]
        return "\n".join(lines)

    def _get_health_info(self) -> str:
        h = self.stock.financial_health
        de = h.debt_to_equity
        de_val = de / 100 if de is not None else None

        # Color code based on health thresholds
        de_color = "green" if de_val and de_val < 0.5 else "yellow" if de_val and de_val < 1 else "red" if de_val else "dim"
        cr = h.current_ratio
        cr_color = "green" if cr and cr > 2 else "yellow" if cr and cr > 1 else "red" if cr else "dim"
        qr = h.quick_ratio
        qr_color = "green" if qr and qr > 1 else "yellow" if qr and qr > 0.5 else "red" if qr else "dim"

        lines = [
            f"D/E Ratio: [{de_color}]{self._fmt(de_val)}[/]",
            f"Current Ratio: [{cr_color}]{self._fmt(cr)}[/]",
            f"Quick Ratio: [{qr_color}]{self._fmt(qr)}[/]",
            "",
            "[dim]D/E<0.5 = low debt. Current",
            "ratio>2 = can pay short-term",
            "debts. Quick ratio>1 = liquid",
            "without selling inventory.[/]",
        ]
        return "\n".join(lines)

    def _get_technical_info(self) -> str:
        t = self.stock.technical
        rsi = t.rsi_14
        rsi_str = f"{rsi:.0f}" if rsi else "N/A"
        rsi_note = ""
        if rsi and rsi < 30:
            rsi_str = f"[green]{rsi_str}[/]"
            rsi_note = " [green](Oversold)[/]"
        elif rsi and rsi > 70:
            rsi_str = f"[red]{rsi_str}[/]"
            rsi_note = " [red](Overbought)[/]"

        # Color MA comparisons
        ma50 = t.price_vs_ma_50_pct
        ma50_color = "red" if ma50 and ma50 < -10 else "yellow" if ma50 and ma50 < 0 else "dim"
        ma200 = t.price_vs_ma_200_pct
        ma200_color = "red" if ma200 and ma200 < -20 else "yellow" if ma200 and ma200 < 0 else "dim"

        lines = [
            f"RSI (14): {rsi_str}{rsi_note}",
            f"vs 50 MA: [{ma50_color}]{self._pct(ma50)}[/]",
            f"vs 200 MA: [{ma200_color}]{self._pct(ma200)}[/]",
            f"From 52W Low: {self._pct(t.pct_from_52w_low)}",
            f"From 52W High: {self._pct(t.pct_from_52w_high)}",
            "",
            "[dim]RSI<30 = oversold (potential",
            "buying opportunity). Below MA",
            "= downtrend. Near 52W low may",
            "signal value if fundamentals OK.[/]",
        ]
        return "\n".join(lines)

    def _get_fair_value_info(self) -> str:
        f = self.stock.fair_value
        price = self.stock.current_price

        lines = []
        if f.graham_number:
            diff = ((f.graham_number - price) / price * 100) if price else 0
            color = "green" if diff > 0 else "red"
            lines.append(f"Graham: ${f.graham_number:.2f} [{color}]({diff:+.1f}%)[/]")

        if f.dcf_value:
            diff = ((f.dcf_value - price) / price * 100) if price else 0
            color = "green" if diff > 0 else "red"
            lines.append(f"DCF: ${f.dcf_value:.2f} [{color}]({diff:+.1f}%)[/]")

        if f.margin_of_safety_pct is not None:
            color = "green" if f.margin_of_safety_pct > 0 else "red"
            lines.append(f"Margin of Safety: [{color}]{f.margin_of_safety_pct:+.1f}%[/]")

        if not lines:
            return "No estimates available"

        # Add narrative
        mos = f.margin_of_safety_pct
        if mos is not None:
            if mos > 30:
                lines.append("")
                lines.append("[green]Strong margin of safety.[/]")
                lines.append("[dim]Trading well below estimated")
                lines.append("fair value - classic value buy.[/]")
            elif mos > 0:
                lines.append("")
                lines.append("[yellow]Some margin of safety.[/]")
                lines.append("[dim]Modestly undervalued but not")
                lines.append("a screaming bargain.[/]")
            else:
                lines.append("")
                lines.append("[red]No margin of safety.[/]")
                lines.append("[dim]Trading above fair value")
                lines.append("estimates - proceed with caution.[/]")

        return "\n".join(lines)

    def _get_buyback_info(self) -> str:
        b = self.stock.buyback
        t = self.stock.technical
        h = self.stock.financial_health

        # Calculate buyback score (0-100)
        score = 0
        reasons = []

        # FCF Yield > 5% is strong (max 25 points)
        fcf_yield = b.fcf_yield_pct
        if fcf_yield:
            fcf_color = "green" if fcf_yield > 8 else "yellow" if fcf_yield > 5 else "dim"
            if fcf_yield > 8:
                score += 25
                reasons.append("High FCF yield")
            elif fcf_yield > 5:
                score += 15
                reasons.append("Good FCF yield")
        else:
            fcf_color = "dim"

        # Low debt (max 20 points)
        de = h.debt_to_equity
        de_val = de / 100 if de else None
        if de_val is not None and de_val < 0.5:
            score += 20
            reasons.append("Low debt")
        elif de_val is not None and de_val < 1:
            score += 10

        # Insider ownership > 5% (max 15 points)
        insider = b.insider_ownership_pct
        if insider and insider > 10:
            score += 15
            reasons.append("High insider ownership")
        elif insider and insider > 5:
            score += 10

        # Near 52-week low (max 20 points) - management buys dips
        pct_from_high = t.pct_from_52w_high
        if pct_from_high and pct_from_high < -30:
            score += 20
            reasons.append("Down >30% from high")
        elif pct_from_high and pct_from_high < -20:
            score += 15
            reasons.append("Down >20% from high")
        elif pct_from_high and pct_from_high < -10:
            score += 10

        # Cash per share (max 20 points)
        cash = b.cash_per_share
        price = self.stock.current_price
        if cash and price and price > 0:
            cash_pct = (cash / price) * 100
            if cash_pct > 20:
                score += 20
                reasons.append("High cash reserves")
            elif cash_pct > 10:
                score += 10

        # Determine score color and label
        if score >= 70:
            score_color = "bold green"
            likelihood = "HIGH"
        elif score >= 50:
            score_color = "green"
            likelihood = "MODERATE"
        elif score >= 30:
            score_color = "yellow"
            likelihood = "LOW"
        else:
            score_color = "dim"
            likelihood = "UNLIKELY"

        lines = [
            f"Buyback Score: [{score_color}]{score}/100 ({likelihood})[/]",
            "",
            f"FCF Yield: [{fcf_color}]{self._pct(fcf_yield) if fcf_yield else 'N/A'}[/]",
            f"Insider Own: {self._pct(insider) if insider else 'N/A'}",
            f"Cash/Share: ${cash:.2f}" if cash else "Cash/Share: N/A",
            f"From 52W High: {self._pct(pct_from_high)}",
        ]

        if reasons:
            lines.append("")
            lines.append(f"[green]+ {', '.join(reasons[:3])}[/]")

        lines.append("")
        lines.append("[dim]Companies with high FCF, low debt,")
        lines.append("insider ownership, and depressed")
        lines.append("prices often announce buybacks.[/]")

        return "\n".join(lines)

    def _fmt(self, val) -> str:
        return f"{val:.2f}" if val is not None else "N/A"

    def _pct(self, val) -> str:
        return f"{val:+.1f}%" if val is not None else "N/A"

    def action_add_to_watchlist(self) -> None:
        if self.remote_provider.add_to_watchlist(self.stock.ticker):
            self.notify(f"Added {self.stock.ticker} to watchlist")
        else:
            self.notify(f"Failed to add {self.stock.ticker} to watchlist", severity="error")

    def action_add_to_long(self) -> None:
        """Add current stock to long list."""
        # Ensure long list exists
        if self.remote_provider.get_list("_long") is None:
            self.remote_provider.create_list("_long", [])
        if self.remote_provider.add_to_list("_long", self.stock.ticker):
            self.notify(f"[green]Added {self.stock.ticker} to LONG list[/]", title="Long List")
        else:
            self.notify(f"{self.stock.ticker} already in long list", severity="warning")

    def action_add_to_short(self) -> None:
        """Add current stock to short list."""
        # Ensure short list exists
        if self.remote_provider.get_list("_short") is None:
            self.remote_provider.create_list("_short", [])
        if self.remote_provider.add_to_list("_short", self.stock.ticker):
            self.notify(f"[red]Added {self.stock.ticker} to SHORT list[/]", title="Short List")
        else:
            self.notify(f"{self.stock.ticker} already in short list", severity="warning")

    def action_deep_research(self) -> None:
        """Fetch and analyze SEC filing with LLM (OpenRouter or Anthropic)."""
        import os
        from tradfi.core.research import deep_research

        # Check for API key (OpenRouter preferred, Anthropic as fallback)
        has_openrouter = os.environ.get("OPENROUTER_API_KEY")
        has_anthropic = os.environ.get("ANTHROPIC_API_KEY")

        if not has_openrouter and not has_anthropic:
            self.notify(
                "Set OPENROUTER_API_KEY or ANTHROPIC_API_KEY to use Deep Research.\n"
                "export OPENROUTER_API_KEY=sk-or-... (free models available)\n"
                "export ANTHROPIC_API_KEY=sk-ant-...",
                title="API Key Required",
                severity="error",
                timeout=10,
            )
            return

        # Update panel to show loading
        research_panel = self.query_one("#research-panel", Static)
        provider = "OpenRouter" if has_openrouter else "Anthropic"
        research_panel.update(
            "[bold yellow]Deep Research[/]\n\n"
            f"[dim]Fetching SEC filing for {self.stock.ticker}...\n"
            f"Using {provider} for analysis. This may take 30-60 seconds.[/]"
        )

        # Run in background thread
        self.run_worker(self._fetch_research, thread=True)

    def _fetch_research(self) -> None:
        """Background worker to fetch and analyze SEC filing."""
        from tradfi.core.research import deep_research

        report = deep_research(self.stock.ticker)
        self.call_from_thread(self._display_research, report)

    def _display_research(self, report) -> None:
        """Display research report in the panel."""
        research_panel = self.query_one("#research-panel", Static)

        if not report:
            research_panel.update(
                "[bold red]Deep Research[/]\n\n"
                "[dim]Could not fetch or analyze SEC filing.\n"
                "The company may not have filings or an error occurred.[/]"
            )
            return

        # Build formatted report
        lines = [
            f"[bold cyan]Deep Research - {report.filing_type}[/] [dim]({report.filing_date})[/]",
            "",
            f"[bold]Summary:[/] {report.summary}",
            "",
            "[bold magenta]Financial Trends[/]",
            f"  Revenue: {report.revenue_trend or 'N/A'}",
            f"  Margins: {report.margin_analysis or 'N/A'}",
            f"  Cash Flow: {report.cash_flow_health or 'N/A'}",
            f"  Debt: {report.debt_situation or 'N/A'}",
            "",
            f"[bold magenta]Management Tone:[/] {report.management_tone or 'N/A'}",
            "",
        ]

        # Health score with color
        health = report.health_score or "N/A"
        health_color = {
            "Strong": "bold green",
            "Moderate": "yellow",
            "Weak": "red",
            "Concerning": "bold red",
        }.get(health, "dim")
        lines.append(f"[bold magenta]Health Score:[/] [{health_color}]{health}[/]")
        lines.append("")

        # Risk factors
        if report.risk_factors:
            lines.append("[bold magenta]Key Risks:[/]")
            for risk in report.risk_factors[:3]:
                lines.append(f"  [red]-[/] {risk}")
            lines.append("")

        # Red flags
        if report.red_flags:
            lines.append("[bold red]Red Flags:[/]")
            for flag in report.red_flags:
                lines.append(f"  [bold red]![/] {flag}")
            lines.append("")

        # Growth drivers
        if report.growth_drivers:
            lines.append("[bold magenta]Growth Drivers:[/]")
            for driver in report.growth_drivers[:3]:
                lines.append(f"  [green]+[/] {driver}")
            lines.append("")

        # Key takeaways
        if report.key_takeaways:
            lines.append("[bold magenta]Key Takeaways:[/]")
            for takeaway in report.key_takeaways:
                lines.append(f"  - {takeaway}")

        research_panel.update("\n".join(lines))

    def action_quarterly_data(self) -> None:
        """Fetch and display quarterly financial trends."""
        # Update panel to show loading
        quarterly_panel = self.query_one("#quarterly-panel", Static)
        quarterly_panel.update(
            "[bold yellow]Quarterly Trends[/]\n\n"
            f"[dim]Fetching quarterly data for {self.stock.ticker}...[/]"
        )

        # Run in background thread
        self.run_worker(self._fetch_quarterly, thread=True)

    def _fetch_quarterly(self) -> None:
        """Background worker to fetch quarterly data."""
        from tradfi.core.quarterly import fetch_quarterly_financials

        trends = fetch_quarterly_financials(self.stock.ticker, periods=8)
        self.call_from_thread(self._display_quarterly, trends)

    def _display_quarterly(self, trends) -> None:
        """Display quarterly trends in the panel."""
        from tradfi.utils.sparkline import sparkline, format_large_number

        quarterly_panel = self.query_one("#quarterly-panel", Static)

        if not trends or not trends.quarters:
            quarterly_panel.update(
                "[bold red]Quarterly Trends[/]\n\n"
                "[dim]Could not fetch quarterly financial data.[/]"
            )
            return

        # Build formatted report
        lines = [
            f"[bold cyan]Quarterly Trends[/] [dim]({len(trends.quarters)} quarters)[/]",
            "",
        ]

        # Revenue
        revenues = trends.get_metric_values("revenue")
        if revenues:
            rev_spark = sparkline(list(reversed(revenues)), width=8)
            latest_rev = format_large_number(revenues[0]) if revenues else "N/A"
            qoq_rev = trends.latest_qoq_revenue_growth
            qoq_str = f" [{'green' if qoq_rev and qoq_rev > 0 else 'red'}]({qoq_rev:+.1f}% QoQ)[/]" if qoq_rev is not None else ""
            lines.append(f"[bold]Revenue:[/]  {latest_rev}  {rev_spark}{qoq_str}")
            lines.append(f"  Trend: [dim]{trends.revenue_trend}[/]")

        # Net Income
        incomes = trends.get_metric_values("net_income")
        if incomes:
            inc_spark = sparkline(list(reversed(incomes)), width=8)
            latest_inc = format_large_number(incomes[0]) if incomes else "N/A"
            qoq_earn = trends.latest_qoq_earnings_growth
            qoq_str = f" [{'green' if qoq_earn and qoq_earn > 0 else 'red'}]({qoq_earn:+.1f}% QoQ)[/]" if qoq_earn is not None else ""
            lines.append(f"[bold]Earnings:[/] {latest_inc}  {inc_spark}{qoq_str}")

        lines.append("")

        # Margins
        lines.append(f"[bold]Margins:[/] [dim]({trends.margin_trend})[/]")
        gm = trends.get_metric_values("gross_margin")
        if gm:
            gm_spark = sparkline(list(reversed(gm)), width=8)
            lines.append(f"  Gross:     {gm[0]:.1f}%  {gm_spark}")

        om = trends.get_metric_values("operating_margin")
        if om:
            om_spark = sparkline(list(reversed(om)), width=8)
            lines.append(f"  Operating: {om[0]:.1f}%  {om_spark}")

        nm = trends.get_metric_values("net_margin")
        if nm:
            nm_spark = sparkline(list(reversed(nm)), width=8)
            lines.append(f"  Net:       {nm[0]:.1f}%  {nm_spark}")

        lines.append("")

        # Recent quarters table
        lines.append("[bold]Recent Quarters:[/]")
        lines.append("[dim]Quarter   Revenue      Net Inc     Margin[/]")
        for q in trends.quarters[:4]:
            rev_str = format_large_number(q.revenue) if q.revenue else "N/A"
            inc_str = format_large_number(q.net_income) if q.net_income else "N/A"
            nm_str = f"{q.net_margin:.1f}%" if q.net_margin else "N/A"
            lines.append(f"{q.quarter}   {rev_str:>10}  {inc_str:>10}  {nm_str:>6}")

        quarterly_panel.update("\n".join(lines))


class ScreenerApp(App):
    """Interactive stock screener TUI."""

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        height: 100%;
    }

    #sidebar {
        width: 30;
        border-right: solid $primary;
        padding: 1;
    }

    #sidebar-title {
        text-align: center;
        text-style: bold;
        color: $secondary;
        padding-bottom: 1;
    }

    #content {
        width: 1fr;
        padding: 1;
    }

    #results-table {
        height: 1fr;
    }

    #bottom-bar {
        height: 3;
        border-top: solid $primary;
        padding: 1;
    }

    #status-bar {
        width: 1fr;
    }

    #api-status {
        width: auto;
        text-align: right;
        padding-right: 1;
    }

    #research-panel {
        border: solid $secondary;
        padding: 1 2;
        margin: 1 0;
        height: auto;
    }

    .section-title {
        text-style: bold;
        color: $primary;
        padding: 1 0;
    }

    #loading {
        align: center middle;
        height: 100%;
        padding: 2;
    }

    #loading-logo {
        text-align: center;
        color: $success;
        padding: 1;
    }

    #loading-text {
        text-align: center;
        text-style: bold;
        color: $secondary;
        padding: 1;
    }

    #loading-detail {
        text-align: center;
        color: $text-muted;
        padding: 0;
    }

    #loading-stats {
        text-align: center;
        color: $primary;
        padding: 1;
    }


    .loading-bar {
        text-align: center;
        color: $success;
    }

    #detail-container {
        padding: 1 2;
    }

    #stock-title {
        text-style: bold;
        text-align: center;
        padding: 1;
    }

    #stock-subtitle {
        text-align: center;
        padding-bottom: 1;
    }

    #top-panels, #bottom-panels {
        height: auto;
        padding: 1 0;
    }

    .info-panel {
        width: 1fr;
        border: solid $primary;
        padding: 1;
        margin: 0 1;
    }

    OptionList {
        height: auto;
        max-height: 10;
    }

    #search-input {
        margin: 0 0 1 0;
    }

    #universe-select {
        height: auto;
        max-height: 8;
        margin-bottom: 1;
    }

    #category-select {
        height: auto;
        max-height: 6;
        margin-bottom: 1;
        display: none;
    }

    #category-title {
        display: none;
    }

    #industry-select {
        height: auto;
        max-height: 12;
        margin-bottom: 1;
    }

    DataTable {
        height: 1fr;
    }

    .sector-header {
        background: $primary;
        color: $text;
        text-style: bold;
        padding: 0 1;
    }

    /* Focus indicators for better UX */
    SelectionList:focus {
        border: double $accent;
    }

    SelectionList:focus-within {
        border: double $accent;
    }

    DataTable:focus {
        border: solid $success;
    }

    Input:focus {
        border: double $accent;
    }

    OptionList:focus {
        border: double $accent;
    }

    #search-input:focus {
        border: double $success;
    }
    """

    # Simplified bindings - most actions now in action menu (Space)
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("space", "show_actions", "Actions", show=True),
        Binding("enter", "select", "Select", show=False),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("/", "focus_search", "Search", show=True),
        Binding("escape", "back", "Back", show=True),
        Binding("?", "help", "Help", show=False),
        # Keep sort keys for power users but hide from footer
        Binding("s", "save_list", "Save List", show=False),
        Binding("u", "focus_universe", "Filter Universe", show=False),
        Binding("f", "focus_industry", "Filter Industry", show=False),
        Binding("c", "clear_filters", "Clear Filters", show=False),
        Binding("1", "sort_ticker", "Sort: Ticker", show=False),
        Binding("i", "sort_industry", "Sort: Industry", show=False),
        Binding("2", "sort_price", "Sort: Price", show=False),
        Binding("3", "sort_1m", "Sort: 1M", show=False),
        Binding("4", "sort_6m", "Sort: 6M", show=False),
        Binding("5", "sort_1y", "Sort: 1Y", show=False),
        Binding("6", "sort_pe", "Sort: P/E", show=False),
        Binding("7", "sort_pb", "Sort: P/B", show=False),
        Binding("8", "sort_roe", "Sort: ROE", show=False),
        Binding("9", "sort_div", "Sort: Div", show=False),
        Binding("0", "sort_rsi", "Sort: RSI", show=False),
        Binding("-", "sort_mos", "Sort: MoS", show=False),
    ]

    # Sort options: (attribute_getter, reverse_default, display_name)
    # reverse_default=True means higher values first by default
    SORT_OPTIONS = {
        "ticker": (lambda s: s.ticker, False, "Ticker"),
        "industry": (lambda s: s.industry or "ZZZ", False, "Industry"),
        "price": (lambda s: s.current_price or 0, True, "Price"),
        "1m": (lambda s: s.technical.return_1m if s.technical.return_1m is not None else float("-inf"), True, "1M"),
        "6m": (lambda s: s.technical.return_6m if s.technical.return_6m is not None else float("-inf"), True, "6M"),
        "1y": (lambda s: s.technical.return_1y if s.technical.return_1y is not None else float("-inf"), True, "1Y"),
        "pe": (lambda s: s.valuation.pe_trailing if s.valuation.pe_trailing and s.valuation.pe_trailing > 0 else float("inf"), False, "P/E"),
        "pb": (lambda s: s.valuation.pb_ratio if s.valuation.pb_ratio and s.valuation.pb_ratio > 0 else float("inf"), False, "P/B"),
        "roe": (lambda s: s.profitability.roe if s.profitability.roe else float("-inf"), True, "ROE"),
        "div": (lambda s: s.dividends.dividend_yield if s.dividends.dividend_yield else 0, True, "Div"),
        "rsi": (lambda s: s.technical.rsi_14 if s.technical.rsi_14 else float("inf"), False, "RSI"),
        "mos": (lambda s: s.fair_value.margin_of_safety_pct if s.fair_value.margin_of_safety_pct else float("-inf"), True, "MoS%"),
    }

    def __init__(self, api_url: str) -> None:
        super().__init__()
        self.current_preset = None
        self.stocks: list[Stock] = []
        self.sectors: dict[str, list[Stock]] = {}
        self.current_sort = "pe"  # Default sort
        self.sort_reverse = False  # Toggle for ascending/descending
        self._viewing_list: str | None = None  # Track if viewing a position list
        self.selected_industries: set[str] = set()  # Selected industries (include)
        self.selected_universes: set[str] = set()  # Selected universes
        self.selected_categories: set[str] = set()  # Selected categories (for ETF universe)
        self._industries_loaded: bool = False  # Track if industries list is populated

        # Remote API provider (required - TUI always uses remote API)
        self.api_url = api_url
        self.remote_provider = RemoteDataProvider(api_url)

    def _get_stock(self, ticker: str) -> Stock | None:
        """Fetch a stock from the remote API."""
        return self.remote_provider.fetch_stock(ticker)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(
                Static("🔍 DEEP VALUE", id="sidebar-title"),
                Static("Search", classes="section-title"),
                Input(placeholder="Ticker (e.g. AAPL)", id="search-input"),
                Static("Universes (toggle)", classes="section-title"),
                SelectionList[str](id="universe-select"),
                Static("Categories", classes="section-title", id="category-title"),
                SelectionList[str](id="category-select"),
                Static("Industries (toggle)", classes="section-title"),
                SelectionList[str](id="industry-select"),
                Static("Presets", classes="section-title"),
                OptionList(
                    "None (Custom)",
                    *[k for k in PRESET_SCREENS.keys()],
                    id="preset-list",
                ),
                Static("My Lists", classes="section-title"),
                OptionList(
                    "📈 Long List",
                    "📉 Short List",
                    id="position-list",
                ),
                id="sidebar",
            ),
            Vertical(
                Container(
                    Static(
                        "[bold cyan]"
                        "                                                                     \n"
                        "              ██████████████████████████████████████████             \n"
                        "          ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░████         \n"
                        "        ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██       \n"
                        "      ██░░░░░░[bold green] ██████╗ ███████╗███████╗██████╗  [/][bold cyan]░░░░░░░░██     \n"
                        "      ██░░░░░░[bold green] ██╔══██╗██╔════╝██╔════╝██╔══██╗ [/][bold cyan]░░░░░░░░██     \n"
                        "      ██░░░░░░[bold green] ██║  ██║█████╗  █████╗  ██████╔╝ [/][bold cyan]░░░░░░░░██     \n"
                        "      ██░░░░░░[bold green] ██║  ██║██╔══╝  ██╔══╝  ██╔═══╝  [/][bold cyan]░░░░░░░░██     \n"
                        "      ██░░░░░░[bold green] ██████╔╝███████╗███████╗██║      [/][bold cyan]░░░░░░░░██     \n"
                        "      ██░░░░░░[bold green] ╚═════╝ ╚══════╝╚══════╝╚═╝      [/][bold cyan]░░░░░░░░██     \n"
                        "      ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██       \n"
                        "      ██░░░░░░[bold green] ██╗   ██╗ █████╗ ██╗     ██╗   ██╗███████╗[/][bold cyan]██     \n"
                        "      ██░░░░░░[bold green] ██║   ██║██╔══██╗██║     ██║   ██║██╔════╝[/][bold cyan]██     \n"
                        "      ██░░░░░░[bold green] ██║   ██║███████║██║     ██║   ██║█████╗  [/][bold cyan]██     \n"
                        "      ██░░░░░░[bold green] ╚██╗ ██╔╝██╔══██║██║     ██║   ██║██╔══╝  [/][bold cyan]██     \n"
                        "      ██░░░░░░[bold green]  ╚████╔╝ ██║  ██║███████╗╚██████╔╝███████╗[/][bold cyan]██     \n"
                        "      ██░░░░░░[bold green]   ╚═══╝  ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝[/][bold cyan]██     \n"
                        "        ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██       \n"
                        "          ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░████         \n"
                        "              ████████████████████████████████████████████           \n"
                        "                                                      ████           \n"
                        "                                                        ████         \n"
                        "                                                          ████       \n"
                        "                                                            ████     \n"
                        "[/][dim magenta]"
                        "                    ~ curiouser and curiouser ~                      \n"
                        "                      ♠    ♥    ♦    ♣                               \n"
                        "[/]",
                        id="loading-logo",
                    ),
                    Static("", id="loading-text"),
                    Static("", id="loading-detail"),
                    Static("", id="loading-stats"),
                    id="loading",
                ),
                DataTable(id="results-table"),
                id="content",
            ),
            id="main-container",
        )
        yield Horizontal(
            Static("[dim]Ready.[/] Press [bold]Space[/] for actions, [bold]/[/] to search, [bold]r[/] to scan.", id="status-bar"),
            Static("[dim]Connecting...[/]", id="api-status"),
            id="bottom-bar",
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.display = False
        table.cursor_type = "row"
        # Simplified columns for cleaner view (8 instead of 14)
        # Focus on key value metrics: Ticker, Price, P/E, ROE, RSI, MoS%, Div, Signal
        table.add_columns("Ticker", "Price", "P/E", "ROE", "RSI", "MoS%", "Div", "Signal")

        # Populate universe selection list
        self._populate_universes()

        # Populate industry selection list
        self._populate_industries()

        # Fetch API status in background
        self.run_worker(self._fetch_api_status, thread=True)

    def _fetch_api_status(self) -> dict | None:
        """Fetch cache stats from the API."""
        import httpx
        try:
            response = httpx.get(
                f"{self.api_url.rstrip('/')}/api/v1/cache/stats",
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    def _format_relative_time(self, timestamp: int | None) -> str:
        """Format a timestamp as relative time."""
        if timestamp is None:
            return "never"
        import time
        age = time.time() - timestamp
        if age < 60:
            return "just now"
        elif age < 3600:
            return f"{int(age / 60)}m ago"
        elif age < 86400:
            return f"{int(age / 3600)}h ago"
        else:
            return f"{int(age / 86400)}d ago"

    def _update_api_status(self, stats: dict | None) -> None:
        """Update the API status widget."""
        try:
            api_status = self.query_one("#api-status", Static)
            if stats:
                total = stats.get("total_cached", 0)
                last_updated = stats.get("last_updated")
                time_str = self._format_relative_time(last_updated)
                # Extract hostname for display
                from urllib.parse import urlparse
                host = urlparse(self.api_url).netloc
                api_status.update(
                    f"[green]●[/] [dim]{host}[/] | "
                    f"[cyan]{total}[/] stocks | "
                    f"[dim]updated {time_str}[/]"
                )
            else:
                api_status.update("[red]●[/] [dim]API disconnected[/]")
        except Exception:
            pass

    def _populate_universes(self) -> None:
        """Populate the universe selection list."""
        try:
            universe_select = self.query_one("#universe-select", SelectionList)

            # Add "ALL" option at the top
            total_count = 0
            for name in AVAILABLE_UNIVERSES.keys():
                try:
                    total_count += len(load_tickers(name))
                except FileNotFoundError:
                    pass
            universe_select.add_option((f"★ ALL ({total_count})", "__all__", False))

            # Add each available universe with ticker count
            for name, info in AVAILABLE_UNIVERSES.items():
                try:
                    tickers = load_tickers(name)
                    count = len(tickers)
                    label = f"{name} ({count})"
                except FileNotFoundError:
                    label = f"{name} (?)"
                universe_select.add_option((label, name, False))
        except Exception:
            pass

    def _populate_industries(self) -> None:
        """Populate the industry selection list from remote API."""
        try:
            industry_select = self.query_one("#industry-select", SelectionList)

            # Get industries from remote API
            industries = self.remote_provider.get_industries()

            if not industries:
                industry_select.add_option(("No cached data", "none", False))
                return

            # Add "ALL" option at the top
            total_stocks = sum(count for _, count in industries)
            industry_select.add_option((f"★ ALL ({total_stocks})", "__all__", False))

            # Sort industries alphabetically and add all
            sorted_industries = sorted(industries, key=lambda x: x[0].lower())
            for industry, count in sorted_industries:
                # Shorten long industry names for display
                display_name = _simplify_industry(industry)
                label = f"{display_name} ({count})"
                industry_select.add_option((label, industry, False))

            self._industries_loaded = True
        except Exception:
            pass

    def _populate_categories(self, universe: str) -> None:
        """Populate the category selection list for a universe."""
        try:
            category_select = self.query_one("#category-select", SelectionList)
            category_title = self.query_one("#category-title", Static)

            # Clear existing options
            category_select.clear_options()
            self.selected_categories = set()

            # Get categories for the universe
            categories = get_universe_categories(universe)

            if not categories:
                # No categories - hide the widget
                category_select.styles.display = "none"
                category_title.styles.display = "none"
                return

            # Show the widget
            category_select.styles.display = "block"
            category_title.styles.display = "block"

            # Add "ALL" option at the top
            category_select.add_option(("★ ALL", "__all__", False))

            # Add each category
            for cat in categories:
                category_select.add_option((cat, cat, False))

        except Exception:
            pass

    def _hide_categories(self) -> None:
        """Hide the category selection widget."""
        try:
            category_select = self.query_one("#category-select", SelectionList)
            category_title = self.query_one("#category-title", Static)
            category_select.styles.display = "none"
            category_title.styles.display = "none"
            self.selected_categories = set()
        except Exception:
            pass

    def on_selection_list_selected_changed(self, event: SelectionList.SelectedChanged) -> None:
        """Handle selection changes for universes, categories, and industries."""
        if event.selection_list.id == "universe-select":
            # Update selected universes (filter out __all__ marker)
            selected = set(event.selection_list.selected)
            if "__all__" in selected:
                self.selected_universes = set()
                self._hide_categories()
            else:
                self.selected_universes = selected
                # Show category selector if exactly one universe with categories is selected
                if len(selected) == 1:
                    universe = list(selected)[0]
                    self._populate_categories(universe)
                else:
                    self._hide_categories()
            self._update_workflow_status()
        elif event.selection_list.id == "category-select":
            # Update selected categories (filter out __all__ marker)
            selected = set(event.selection_list.selected)
            if "__all__" in selected:
                self.selected_categories = set()
            else:
                self.selected_categories = selected
            self._update_workflow_status()
        elif event.selection_list.id == "industry-select":
            # Update selected industries (filter out __all__ marker)
            selected = set(event.selection_list.selected)
            if "__all__" in selected:
                self.selected_industries = set()
            else:
                self.selected_industries = selected
            self._update_workflow_status()

    def _update_workflow_status(self) -> None:
        """Update status bar with contextual workflow guidance."""
        # Count total tickers based on selection
        total_tickers = 0
        universes_to_check = self.selected_universes if self.selected_universes else set(AVAILABLE_UNIVERSES.keys())
        for name in universes_to_check:
            try:
                if self.selected_categories:
                    total_tickers += len(load_tickers_by_categories(name, self.selected_categories))
                else:
                    total_tickers += len(load_tickers(name))
            except FileNotFoundError:
                pass

        # Build status message
        parts = []
        if self.selected_universes:
            count = len(self.selected_universes)
            parts.append(f"{count} universe{'s' if count > 1 else ''}")
        else:
            parts.append("all universes")

        if self.selected_categories:
            count = len(self.selected_categories)
            parts.append(f"{count} categor{'ies' if count > 1 else 'y'}")

        if self.selected_industries:
            count = len(self.selected_industries)
            parts.append(f"{count} industr{'ies' if count > 1 else 'y'}")

        filter_desc = " + ".join(parts)
        preset_info = f" [{self.current_preset}]" if self.current_preset else ""

        self._update_status(
            f"[bold]Filters:[/] {filter_desc}{preset_info} (~{total_tickers} stocks). "
            f"Press [bold]r[/] to scan."
        )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "preset-list":
            selected = str(event.option.prompt)
            self.current_preset = None if selected == "None (Custom)" else selected
            self._run_screen()
        elif event.option_list.id == "position-list":
            selected = str(event.option.prompt)
            if "Long" in selected:
                self._load_position_list("_long", "Long List")
            elif "Short" in selected:
                self._load_position_list("_short", "Short List")

    def _run_screen(self) -> None:
        # Clear position list view flag - we're now screening
        self._viewing_list = None

        loading = self.query_one("#loading", Container)
        table = self.query_one("#results-table", DataTable)
        loading.display = True
        table.display = False

        # Build description
        if not self.selected_universes:
            universe_desc = "all universes"
        elif len(self.selected_universes) <= 2:
            universe_desc = " + ".join(sorted(self.selected_universes))
        else:
            universe_desc = f"{len(self.selected_universes)} universes"

        preset_desc = f" [{self.current_preset}]" if self.current_preset else ""
        industry_desc = f" ({len(self.selected_industries)} industries)" if self.selected_industries else ""

        loading_text = self.query_one("#loading-text", Static)
        loading_text.update(f"[cyan]SCANNING {universe_desc.upper()}[/]{preset_desc}{industry_desc}")

        loading_detail = self.query_one("#loading-detail", Static)
        loading_detail.update("[dim]Initializing...[/]")

        loading_stats = self.query_one("#loading-stats", Static)
        loading_stats.update("")

        self.run_worker(self._fetch_stocks, exclusive=True, thread=True)

    def _load_position_list(self, list_name: str, display_name: str) -> None:
        """Load and display a position list (long or short)."""
        list_data = self.remote_provider.get_list(list_name)
        tickers = list_data.get("tickers", []) if list_data else []

        if not tickers:
            self.notify(f"{display_name} is empty.\nAdd stocks with 'l' (long) or 'x' (short) in detail view.",
                       title=display_name, severity="warning", timeout=5)
            return

        loading = self.query_one("#loading", Container)
        table = self.query_one("#results-table", DataTable)
        loading.display = True
        table.display = False

        loading_text = self.query_one("#loading-text", Static)
        loading_text.update(f"[cyan]LOADING {display_name.upper()}[/]")

        loading_detail = self.query_one("#loading-detail", Static)
        loading_detail.update("[dim]Initializing...[/]")

        loading_stats = self.query_one("#loading-stats", Static)
        loading_stats.update(f"[dim]{len(tickers)} positions[/]")

        # Store which list we're viewing for status bar
        self._viewing_list = display_name

        self.run_worker(
            lambda: self._fetch_position_stocks(tickers),
            exclusive=True,
            thread=True
        )

    def _fetch_position_stocks(self, tickers: list[str]) -> list[Stock]:
        """Fetch stock data for a position list."""
        stocks = []
        total = len(tickers)

        for i, ticker in enumerate(tickers):
            progress = (i + 1) / total * 100
            self.call_from_thread(
                self._update_progress, ticker, i + 1, total,
                len(stocks), progress, 0, False
            )

            stock = self._get_stock(ticker)
            if stock:
                stocks.append(stock)

        return stocks

    def _fetch_stocks(self) -> list[Stock]:
        # Build ticker list based on universe selection
        ticker_set: set[str] = set()

        if self.selected_universes:
            # Load from selected universes
            for name in self.selected_universes:
                try:
                    # If categories are selected, filter by them
                    if self.selected_categories:
                        tickers = load_tickers_by_categories(name, self.selected_categories)
                        ticker_set.update(tickers)
                    else:
                        ticker_set.update(load_tickers(name))
                except FileNotFoundError:
                    pass
        else:
            # No universes selected - load all
            for name in AVAILABLE_UNIVERSES.keys():
                try:
                    ticker_set.update(load_tickers(name))
                except FileNotFoundError:
                    pass

        ticker_list = sorted(ticker_set)

        if not ticker_list:
            return []

        # Get criteria
        if self.current_preset and self.current_preset in PRESET_SCREENS:
            criteria = PRESET_SCREENS[self.current_preset]
        else:
            criteria = ScreenCriteria()  # No filter - show all stocks

        passing_stocks = []
        total = len(ticker_list)
        fetched = 0

        for i, ticker in enumerate(ticker_list):
            # Update progress via call_from_thread
            progress = (i + 1) / total * 100
            self.call_from_thread(
                self._update_progress, ticker, i + 1, total,
                len(passing_stocks), progress, fetched
            )

            stock = self._get_stock(ticker)
            if stock:
                fetched += 1

                # Apply screening criteria
                if not screen_stock(stock, criteria):
                    continue

                # Apply industry filter (if any industries are selected)
                if self.selected_industries:
                    if stock.industry not in self.selected_industries:
                        continue

                passing_stocks.append(stock)

        return passing_stocks

    def _update_progress(self, ticker: str, current: int, total: int, found: int,
                         progress: float, fetched: int) -> None:
        try:
            # Current ticker being processed
            loading_detail = self.query_one("#loading-detail", Static)
            loading_detail.update(f"[green]⚡[/] [bold]{ticker}[/]")

            # Stats line
            loading_stats = self.query_one("#loading-stats", Static)
            pct = int(progress)
            loading_stats.update(
                f"[dim]Progress:[/] {current}/{total} ({pct}%)  "
                f"[dim]Found:[/] [green]{found}[/]  "
                f"[dim]Fetched:[/] {fetched}"
            )
        except Exception:
            pass  # Ignore if widgets not available

    def _update_status(self, msg: str) -> None:
        status = self.query_one("#status-bar", Static)
        status.update(msg)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state.name == "SUCCESS":
            # Check if this is the API status worker
            if event.worker.name == "_fetch_api_status":
                self._update_api_status(event.worker.result)
            elif event.worker.name == "_resync_all_universes":
                # Resync completed
                result = event.worker.result or {"triggered": 0, "failed": 0, "universes": []}
                self.notify(
                    f"Resync triggered for {result['triggered']} universes "
                    f"({result['failed']} failed)",
                    title="Resync Complete",
                    timeout=10,
                )
                # Refresh the screen to show updated data
                self._run_screen()
            else:
                # Stock fetch worker
                self.stocks = event.worker.result or []
                self._populate_table()

    def _populate_table(self) -> None:
        loading = self.query_one("#loading", Container)
        table = self.query_one("#results-table", DataTable)

        loading.display = False
        table.display = True
        table.clear()

        # Sort stocks according to current sort setting
        sort_key, default_reverse, sort_name = self.SORT_OPTIONS[self.current_sort]
        # XOR with sort_reverse to toggle direction
        reverse = default_reverse != self.sort_reverse
        sorted_stocks = sorted(self.stocks, key=sort_key, reverse=reverse)

        # Add rows - simplified 8 columns for cleaner view
        for stock in sorted_stocks:
            # Format key values
            price = f"${stock.current_price:.0f}" if stock.current_price else "-"
            pe = f"{stock.valuation.pe_trailing:.1f}" if stock.valuation.pe_trailing and isinstance(stock.valuation.pe_trailing, (int, float)) else "-"
            roe = f"{stock.profitability.roe:.0f}%" if stock.profitability.roe else "-"
            rsi = f"{stock.technical.rsi_14:.0f}" if stock.technical.rsi_14 else "-"

            # Margin of Safety
            mos_val = stock.fair_value.margin_of_safety_pct
            mos = f"{mos_val:+.0f}%" if mos_val else "-"

            # Dividend yield
            div_val = stock.dividends.dividend_yield
            div = f"{div_val:.1f}%" if div_val else "-"

            signal = stock.signal

            table.add_row(
                stock.ticker,
                price,
                pe,
                roe,
                rsi,
                mos,
                div,
                signal,
                key=stock.ticker,
            )

        # Update status with sort info and active filters
        direction = "↓" if reverse else "↑"
        if self._viewing_list:
            # Viewing a position list
            self._update_status(
                f"{self._viewing_list}: {len(self.stocks)} stocks. "
                f"Sort: {sort_name} {direction}. Space=actions, Enter=details."
            )
        else:
            # Build filter info
            filter_parts = []
            if self.selected_universes:
                count = len(self.selected_universes)
                filter_parts.append(f"{count} univ")
            if self.selected_industries:
                count = len(self.selected_industries)
                filter_parts.append(f"{count} ind")

            filter_info = f" [{', '.join(filter_parts)}]" if filter_parts else ""
            preset_info = f" ({self.current_preset})" if self.current_preset else ""

            # Show universe names if few selected, otherwise count
            if not self.selected_universes:
                universe_display = "ALL"
            elif len(self.selected_universes) <= 2:
                universe_display = "+".join(sorted(self.selected_universes))
            else:
                universe_display = f"{len(self.selected_universes)} universes"

            self._update_status(
                f"Found {len(self.stocks)} in {universe_display}{preset_info}{filter_info}. "
                f"Sort: {sort_name} {direction}. Space=actions, Enter=details."
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        ticker = str(event.row_key.value)
        # Find the stock
        for stock in self.stocks:
            if stock.ticker == ticker:
                self.push_screen(StockDetailScreen(stock, self.remote_provider))
                break

    def action_refresh(self) -> None:
        self._run_screen()

    def action_back(self) -> None:
        if len(self.screen_stack) > 1:
            self.pop_screen()

    def action_show_actions(self) -> None:
        """Show the action menu."""
        def handle_action(action_id: str | None) -> None:
            if action_id is None:
                return
            # Map action IDs to methods
            action_map = {
                "search": self.action_focus_search,
                "universe": self.action_focus_universe,
                "industry": self.action_focus_industry,
                "clear": self.action_clear_filters,
                "refresh": self.action_refresh,
                "save": self.action_save_list,
                "clear_cache": self.action_clear_cache,
                "resync": self.action_resync_universes,
                "help": self.action_help,
                "sort_pe": self.action_sort_pe,
                "sort_mos": self.action_sort_mos,
                "sort_rsi": self.action_sort_rsi,
                "sort_roe": self.action_sort_roe,
                "sort_div": self.action_sort_div,
                "sort_price": self.action_sort_price,
                "sort_1m": self.action_sort_1m,
                "sort_6m": self.action_sort_6m,
                "sort_1y": self.action_sort_1y,
                "sort_ticker": self.action_sort_ticker,
                "sort_industry": self.action_sort_industry,
                "sort_pb": self.action_sort_pb,
            }
            if action_id in action_map:
                action_map[action_id]()

        self.push_screen(ActionMenuScreen(), handle_action)

    def action_help(self) -> None:
        self.notify(
            "Quick Keys:\n"
            "Space - Action menu (all commands)\n"
            "/ - Search ticker | r - Refresh | q - Quit\n"
            "Enter - View details | Esc - Go back\n"
            "\n"
            "In action menu, press any key to execute that action.\n"
            "\n"
            "Detail view: l=Long x=Short w=Watchlist d=Research",
            title="Help",
            timeout=10,
        )

    def action_clear_cache(self) -> None:
        """Clear all cached stock data on the server."""
        count = self.remote_provider.clear_cache()
        self.notify(f"Cleared {count} cached entries on server", title="Cache Cleared")

    def action_resync_universes(self) -> None:
        """Resync all universes by triggering server-side refresh."""
        self.notify("Triggering server-side resync of all universes...", title="Resync")
        self.run_worker(self._resync_all_universes, exclusive=True, thread=True)

    def _resync_all_universes(self) -> dict:
        """Worker to trigger server-side resync for all universes."""
        import time

        results = {"triggered": 0, "failed": 0, "universes": []}

        for name in AVAILABLE_UNIVERSES.keys():
            try:
                result = self.remote_provider.trigger_refresh(name)
                if "error" not in result:
                    results["triggered"] += 1
                    results["universes"].append(name)
                    self.call_from_thread(
                        self.notify,
                        f"Triggered refresh for {name}",
                        title="Resyncing...",
                    )
                else:
                    results["failed"] += 1
            except Exception:
                results["failed"] += 1

            # Small delay between triggering refreshes
            time.sleep(1.0)

        return results

    def _sort_by(self, sort_key: str) -> None:
        """Sort table by the given key, toggling direction if same key."""
        if not self.stocks:
            return

        if self.current_sort == sort_key:
            # Toggle direction
            self.sort_reverse = not self.sort_reverse
        else:
            # New sort key, reset direction
            self.current_sort = sort_key
            self.sort_reverse = False

        self._populate_table()

    def action_sort_ticker(self) -> None:
        self._sort_by("ticker")

    def action_sort_industry(self) -> None:
        self._sort_by("industry")

    def action_sort_price(self) -> None:
        self._sort_by("price")

    def action_sort_1m(self) -> None:
        self._sort_by("1m")

    def action_sort_6m(self) -> None:
        self._sort_by("6m")

    def action_sort_1y(self) -> None:
        self._sort_by("1y")

    def action_sort_pe(self) -> None:
        self._sort_by("pe")

    def action_sort_pb(self) -> None:
        self._sort_by("pb")

    def action_sort_roe(self) -> None:
        self._sort_by("roe")

    def action_sort_div(self) -> None:
        self._sort_by("div")

    def action_sort_rsi(self) -> None:
        self._sort_by("rsi")

    def action_sort_mos(self) -> None:
        self._sort_by("mos")

    def action_save_list(self) -> None:
        """Save current screen results to a named list."""
        if not self.stocks:
            self.notify("No results to save. Run a screen first.", severity="warning")
            return

        # Generate list name from universe and preset
        preset_name = self.current_preset or "custom"
        if not self.selected_universes:
            universe_name = "all"
        elif len(self.selected_universes) == 1:
            universe_name = list(self.selected_universes)[0]
        else:
            universe_name = f"{len(self.selected_universes)}univ"
        list_name = f"{universe_name}-{preset_name}"

        # Save the list via remote API
        tickers = [s.ticker for s in self.stocks]
        if self.remote_provider.create_list(list_name, tickers):
            self.notify(
                f"Saved {len(tickers)} stocks to '{list_name}'\n"
                f"View with: tradfi list show {list_name}",
                title="List Saved",
                timeout=5,
            )
        else:
            self.notify(
                f"Failed to save list '{list_name}' to server",
                title="Save Failed",
                severity="error",
            )

    def action_focus_search(self) -> None:
        """Focus the search input."""
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

    def action_focus_universe(self) -> None:
        """Focus the universe selection list."""
        universe_select = self.query_one("#universe-select", SelectionList)
        universe_select.focus()

    def action_focus_industry(self) -> None:
        """Focus the industry selection list."""
        industry_select = self.query_one("#industry-select", SelectionList)
        industry_select.focus()

    def action_clear_filters(self) -> None:
        """Clear all universe, category, and industry selections."""
        try:
            universe_select = self.query_one("#universe-select", SelectionList)
            universe_select.deselect_all()
            self.selected_universes = set()

            # Clear and hide categories
            self._hide_categories()

            industry_select = self.query_one("#industry-select", SelectionList)
            industry_select.deselect_all()
            self.selected_industries = set()

            self.notify("All filters cleared", timeout=2)
            self._run_screen()
        except Exception:
            pass

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "search-input":
            ticker = event.value.strip().upper()
            if ticker:
                self._search_ticker(ticker)
                event.input.value = ""  # Clear the input

    def _search_ticker(self, ticker: str) -> None:
        """Search for a single ticker and display it."""
        loading = self.query_one("#loading", Container)
        table = self.query_one("#results-table", DataTable)
        loading.display = True
        table.display = False

        loading_text = self.query_one("#loading-text", Static)
        loading_text.update(f"[cyan]SEARCHING[/]")

        loading_detail = self.query_one("#loading-detail", Static)
        loading_detail.update(f"[bold]{ticker}[/]")

        loading_stats = self.query_one("#loading-stats", Static)
        loading_stats.update("[dim]Fetching data...[/]")

        self._viewing_list = f"Search: {ticker}"

        self.run_worker(
            lambda: self._fetch_single_stock(ticker),
            exclusive=True,
            thread=True
        )

    def _fetch_single_stock(self, ticker: str) -> list[Stock]:
        """Fetch a single stock by ticker."""
        stock = self._get_stock(ticker)
        if stock:
            return [stock]
        return []


def run_tui(api_url: str) -> None:
    """Run the interactive TUI.

    Args:
        api_url: Remote API URL (required). All data is fetched from the
                 remote server - no local yfinance fetching.
    """
    app = ScreenerApp(api_url=api_url)
    app.run()
