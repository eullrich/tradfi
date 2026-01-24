"""Main TUI application for tradfi."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    OptionList,
    SelectionList,
    Static,
)
from textual.worker import Worker

# Filter pill types for color coding
FILTER_PILL_COLORS = {
    "universe": "cyan",
    "sector": "yellow",
    "preset": "green",
    "category": "magenta",
}

# ETF category icons for quick visual recognition
ETF_CATEGORY_ICONS = {
    "REITs": "🏢",
    "Commodities": "⚡",
    "Sectors": "📊",
    "International": "🌍",
}

# Column configurations for different asset types
STOCK_COLUMNS = ("Company", "Sector", "Price", "P/E", "ROE", "RSI", "MoS%", "Div", "Signal")
ETF_COLUMNS = ("Company", "Category", "Price", "ExpRatio", "AUM", "YTD", "1Y", "Yield", "Signal")
MIXED_COLUMNS = ("Company", "Type", "Sector", "Price", "Yield", "1Y", "RSI", "Signal")


class FilterPill(Static):
    """A removable filter pill showing [name ×]."""

    class Removed(Message):
        """Message sent when a filter pill is removed."""

        def __init__(self, filter_type: str, filter_value: str) -> None:
            super().__init__()
            self.filter_type = filter_type
            self.filter_value = filter_value

    def __init__(
        self,
        filter_type: str,
        filter_value: str,
        display_name: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.filter_type = filter_type
        self.filter_value = filter_value
        self.display_name = display_name or filter_value
        self._update_display()

    def _update_display(self) -> None:
        """Update the pill display text."""
        color = FILTER_PILL_COLORS.get(self.filter_type, "white")
        # Truncate long names
        name = self.display_name
        if len(name) > 15:
            name = name[:13] + ".."
        self.update(f"[{color}][{name} ×][/{color}]")

    def on_click(self) -> None:
        """Handle click to remove the pill."""
        self.post_message(self.Removed(self.filter_type, self.filter_value))


class ClearAllPill(Static):
    """A 'Clear All' button pill."""

    class Clicked(Message):
        """Message sent when Clear All is clicked."""
        pass

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.update("[red bold][Clear All][/]")

    def on_click(self) -> None:
        """Handle click to clear all filters."""
        self.post_message(self.Clicked())


class FilterPillsContainer(Horizontal):
    """Container for all active filter pills."""

    DEFAULT_CSS = """
    FilterPillsContainer {
        height: auto;
        min-height: 0;
        padding: 0 0 1 0;
        display: none;
    }

    FilterPillsContainer.has-pills {
        display: block;
        min-height: 2;
    }

    FilterPill {
        width: auto;
        margin: 0 1 0 0;
        padding: 0 1;
        background: $surface-darken-1;
    }

    FilterPill:hover {
        background: $surface-lighten-1;
        text-style: bold;
    }

    ClearAllPill {
        width: auto;
        margin: 0 0 0 1;
        padding: 0 1;
        background: $error-darken-2;
    }

    ClearAllPill:hover {
        background: $error;
        text-style: bold;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def update_pills(
        self,
        universes: set[str],
        sectors: set[str],
        categories: set[str],
        preset: str | None,
    ) -> None:
        """Update the pills based on current filter state."""
        # Remove all existing children
        self.remove_children()

        has_any = bool(universes or sectors or categories or preset)

        if not has_any:
            self.remove_class("has-pills")
            return

        self.add_class("has-pills")

        # Add universe pills
        for universe in sorted(universes):
            self.mount(FilterPill(
                filter_type="universe",
                filter_value=universe,
                display_name=universe,
            ))

        # Add category pills
        for category in sorted(categories):
            self.mount(FilterPill(
                filter_type="category",
                filter_value=category,
                display_name=category,
            ))

        # Add sector pills
        for sector in sorted(sectors):
            # Truncate sector names for display
            display = sector if len(sector) <= 20 else sector[:18] + ".."
            self.mount(FilterPill(
                filter_type="sector",
                filter_value=sector,
                display_name=display,
            ))

        # Add preset pill
        if preset:
            self.mount(FilterPill(
                filter_type="preset",
                filter_value=preset,
                display_name=preset,
            ))

        # Add Clear All button if we have multiple filters
        total_filters = len(universes) + len(sectors) + len(categories) + (1 if preset else 0)
        if total_filters > 1:
            self.mount(ClearAllPill())


# Action menu categories and items
ACTION_MENU_ITEMS = {
    "Navigate": [
        ("search", "/", "Search ticker"),
        ("universe", "u", "Filter by universe"),
        ("sector", "f", "Filter by sector/category"),
        ("clear", "c", "Clear all filters"),
    ],
    "Discovery": [
        ("preset_fallen", "F", "Fallen Angels (quality down 30%+)"),
        ("preset_hidden", "H", "Hidden Gems (small/mid quality)"),
        ("preset_turnaround", "T", "Turnaround Candidates"),
        ("preset_momentum", "M", "Momentum + Value"),
        ("preset_dividend", "D", "Dividend Growers"),
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
        ("sort_sector", "i", "Sector"),
        ("sort_pb", "7", "P/B ratio"),
    ],
    "Actions": [
        ("refresh", "r", "Refresh / Run screen"),
        ("save", "s", "Save current list"),
        ("cache_manage", "K", "Cache Manager"),
        ("clear_cache", "C", "Clear cache"),
        ("resync", "R", "Resync all universes"),
    ],
    "View": [
        ("help", "?", "Show all shortcuts"),
        ("heatmap", "h", "Sector Heatmap"),
        ("scatter", "p", "Scatter Plot"),
        ("currency", "$", "Toggle display currency"),
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

from tradfi.core.remote_provider import RemoteDataProvider
from tradfi.core.screener import (
    AVAILABLE_UNIVERSES,
    PRESET_DESCRIPTIONS,
    PRESET_INFO,
    PRESET_SCREENS,
    ScreenCriteria,
    find_similar_stocks,
    get_universe_categories,
    load_tickers,
    load_tickers_by_categories,
    screen_stock,
)
from tradfi.models.stock import Stock
from tradfi.utils.sparkline import ascii_bar, ascii_scatter

# Metrics available for heatmap and scatter plot
VISUALIZATION_METRICS = {
    "rsi": ("RSI", lambda s: s.technical.rsi_14, False),  # (label, getter, reverse_bar)
    "pe": ("P/E", lambda s: s.valuation.pe_trailing if s.valuation.pe_trailing and isinstance(s.valuation.pe_trailing, (int, float)) and s.valuation.pe_trailing > 0 else None, True),
    "roe": ("ROE %", lambda s: s.profitability.roe, False),
    "return_1m": ("1M Return", lambda s: s.technical.return_1m, False),
    "mos": ("MoS %", lambda s: s.fair_value.margin_of_safety_pct, False),
    "div": ("Div Yield", lambda s: s.dividends.dividend_yield, False),
    "pb": ("P/B", lambda s: s.valuation.pb_ratio if s.valuation.pb_ratio and s.valuation.pb_ratio > 0 else None, True),
}


class SectorHeatmapScreen(ModalScreen):
    """Modal showing sector performance heatmap."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("1", "metric_rsi", "RSI"),
        Binding("2", "metric_pe", "P/E"),
        Binding("3", "metric_roe", "ROE"),
        Binding("4", "metric_return", "1M Return"),
        Binding("5", "metric_mos", "MoS"),
        Binding("enter", "select_sector", "Filter"),
    ]

    CSS = """
    SectorHeatmapScreen {
        align: center middle;
    }

    #heatmap-container {
        width: 72;
        max-height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #heatmap-title {
        text-align: center;
        text-style: bold;
        color: $secondary;
        padding-bottom: 1;
    }

    #heatmap-content {
        padding: 0 1;
    }

    #heatmap-footer {
        text-align: center;
        color: $text-muted;
        padding-top: 1;
        border-top: solid $primary;
        margin-top: 1;
    }
    """

    def __init__(self, stocks: list[Stock]) -> None:
        super().__init__()
        self.stocks = stocks
        self.current_metric = "rsi"
        self.sector_stats = {}
        self.selected_index = 0
        self.sector_list = []

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="heatmap-container"):
            yield Static("[bold cyan]Sector Heatmap[/]", id="heatmap-title")
            yield Static("", id="heatmap-content")
            yield Static(
                "[dim]1=RSI 2=P/E 3=ROE 4=Return 5=MoS | Enter=Filter | Esc=Close[/]",
                id="heatmap-footer"
            )

    def on_mount(self) -> None:
        self._calculate_stats()
        self._render_heatmap()

    def _calculate_stats(self) -> None:
        """Aggregate stocks by sector."""
        self.sector_stats = {}

        for stock in self.stocks:
            sector = stock.sector or "Unknown"
            if sector not in self.sector_stats:
                self.sector_stats[sector] = {
                    "count": 0,
                    "rsi": [],
                    "pe": [],
                    "roe": [],
                    "return_1m": [],
                    "mos": [],
                }

            self.sector_stats[sector]["count"] += 1

            # Collect metrics
            if stock.technical.rsi_14:
                self.sector_stats[sector]["rsi"].append(stock.technical.rsi_14)
            pe = stock.valuation.pe_trailing
            if pe and isinstance(pe, (int, float)) and pe > 0:
                self.sector_stats[sector]["pe"].append(pe)
            if stock.profitability.roe is not None:
                self.sector_stats[sector]["roe"].append(stock.profitability.roe)
            if stock.technical.return_1m is not None:
                self.sector_stats[sector]["return_1m"].append(stock.technical.return_1m)
            if stock.fair_value.margin_of_safety_pct is not None:
                self.sector_stats[sector]["mos"].append(stock.fair_value.margin_of_safety_pct)

        # Sort by stock count descending
        self.sector_list = sorted(
            self.sector_stats.keys(),
            key=lambda s: self.sector_stats[s]["count"],
            reverse=True
        )

    def _render_heatmap(self) -> None:
        """Render the heatmap display."""
        content = self.query_one("#heatmap-content", Static)
        title = self.query_one("#heatmap-title", Static)

        metric_label, getter, reverse = VISUALIZATION_METRICS[self.current_metric]
        title.update(f"[bold cyan]Sector Heatmap - {metric_label}[/]")

        if not self.sector_stats:
            content.update("[dim]No sector data available[/]")
            return

        # Calculate min/max for bar scaling
        all_values = []
        for sector in self.sector_list:
            values = self.sector_stats[sector].get(self.current_metric, [])
            if values:
                all_values.append(sum(values) / len(values))

        if not all_values:
            content.update("[dim]No data for selected metric[/]")
            return

        min_val = min(all_values)
        max_val = max(all_values)

        lines = [
            "[dim]Sector              Bar              Value   Count[/]",
            "─" * 60,
        ]

        for i, sector in enumerate(self.sector_list):
            values = self.sector_stats[sector].get(self.current_metric, [])
            count = self.sector_stats[sector]["count"]

            if values:
                avg_val = sum(values) / len(values)
                bar = ascii_bar(avg_val, min_val, max_val, width=14, reverse=reverse)

                # Color based on metric and value
                if self.current_metric == "rsi":
                    if avg_val < 35:
                        color = "green"
                        label = "Oversold"
                    elif avg_val > 65:
                        color = "red"
                        label = "Overbought"
                    else:
                        color = "yellow"
                        label = ""
                elif self.current_metric == "pe":
                    if avg_val < 15:
                        color = "green"
                        label = "Cheap"
                    elif avg_val > 25:
                        color = "red"
                        label = "Expensive"
                    else:
                        color = "yellow"
                        label = ""
                elif self.current_metric in ("roe", "mos", "return_1m"):
                    if avg_val > 15:
                        color = "green"
                        label = ""
                    elif avg_val < 0:
                        color = "red"
                        label = ""
                    else:
                        color = "yellow"
                        label = ""
                else:
                    color = "dim"
                    label = ""

                # Highlight selected row
                sector_display = f"{sector[:18]:<18}"
                if i == self.selected_index:
                    sector_display = f"[bold reverse]{sector_display}[/]"

                val_str = f"{avg_val:>6.1f}"
                label_str = f" [{color}]{label}[/]" if label else ""

                lines.append(
                    f"{sector_display} [{color}]{bar}[/]  {val_str}  ({count:>3}){label_str}"
                )
            else:
                sector_display = f"{sector[:18]:<18}"
                if i == self.selected_index:
                    sector_display = f"[bold reverse]{sector_display}[/]"
                lines.append(f"{sector_display} [dim]{'░' * 14}[/]     N/A  ({count:>3})")

        content.update("\n".join(lines))

    def on_key(self, event) -> None:
        """Handle navigation keys."""
        if event.key == "up" and self.selected_index > 0:
            self.selected_index -= 1
            self._render_heatmap()
        elif event.key == "down" and self.selected_index < len(self.sector_list) - 1:
            self.selected_index += 1
            self._render_heatmap()

    def action_metric_rsi(self) -> None:
        self.current_metric = "rsi"
        self._render_heatmap()

    def action_metric_pe(self) -> None:
        self.current_metric = "pe"
        self._render_heatmap()

    def action_metric_roe(self) -> None:
        self.current_metric = "roe"
        self._render_heatmap()

    def action_metric_return(self) -> None:
        self.current_metric = "return_1m"
        self._render_heatmap()

    def action_metric_mos(self) -> None:
        self.current_metric = "mos"
        self._render_heatmap()

    def action_select_sector(self) -> None:
        """Return selected sector to filter main table."""
        if self.sector_list:
            selected_sector = self.sector_list[self.selected_index]
            self.dismiss(selected_sector)
        else:
            self.dismiss(None)


class ScatterPlotScreen(ModalScreen):
    """Modal showing scatter plot of two metrics."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("x", "cycle_x", "Change X"),
        Binding("y", "cycle_y", "Change Y"),
    ]

    CSS = """
    ScatterPlotScreen {
        align: center middle;
    }

    #scatter-container {
        width: 80;
        height: 32;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #scatter-title {
        text-align: center;
        text-style: bold;
        color: $secondary;
        padding-bottom: 1;
    }

    #scatter-plot {
        padding: 0;
    }

    #scatter-legend {
        padding-top: 1;
    }

    #scatter-footer {
        text-align: center;
        color: $text-muted;
        padding-top: 1;
        border-top: solid $primary;
    }
    """

    METRIC_KEYS = ["pe", "pb", "roe", "rsi", "mos", "return_1m", "div"]

    def __init__(self, stocks: list[Stock]) -> None:
        super().__init__()
        self.stocks = stocks
        self.x_metric = "pe"
        self.y_metric = "roe"

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="scatter-container"):
            yield Static("[bold cyan]Scatter Plot[/]", id="scatter-title")
            yield Static("", id="scatter-plot")
            yield Static("", id="scatter-legend")
            yield Static(
                "[dim]x=Change X axis | y=Change Y axis | Esc=Close[/]",
                id="scatter-footer"
            )

    def on_mount(self) -> None:
        self._render_plot()

    def _render_plot(self) -> None:
        """Render the scatter plot."""
        title = self.query_one("#scatter-title", Static)
        plot_area = self.query_one("#scatter-plot", Static)
        legend = self.query_one("#scatter-legend", Static)

        x_label, x_getter, _ = VISUALIZATION_METRICS[self.x_metric]
        y_label, y_getter, _ = VISUALIZATION_METRICS[self.y_metric]

        title.update(f"[bold cyan]Scatter: {x_label} vs {y_label}[/]")

        # Collect points
        points = []
        for stock in self.stocks:
            x_val = x_getter(stock)
            y_val = y_getter(stock)
            if x_val is not None and y_val is not None:
                points.append((x_val, y_val, stock.ticker))

        if not points:
            plot_area.update("[dim]No valid data points for selected metrics[/]")
            legend.update("")
            return

        # Generate scatter plot
        plot_str = ascii_scatter(
            points,
            width=55,
            height=15,
            x_label=x_label,
            y_label=y_label,
        )

        plot_area.update(plot_str)

        # Build legend with quadrant hints
        if self.x_metric == "pe" and self.y_metric == "roe":
            legend.update(
                "[green]■[/] Value (low P/E + high ROE)  "
                "[yellow]■[/] Growth (high P/E + high ROE)  "
                "[red]■[/] Trap? (low P/E + low ROE)"
            )
        elif self.x_metric == "rsi":
            legend.update(
                f"[green]←[/] Oversold (RSI < 30)  "
                f"[red]→[/] Overbought (RSI > 70)  "
                f"[dim]{len(points)} stocks plotted[/]"
            )
        else:
            legend.update(f"[dim]{len(points)} stocks plotted[/]")

    def action_cycle_x(self) -> None:
        """Cycle to next X metric."""
        idx = self.METRIC_KEYS.index(self.x_metric)
        self.x_metric = self.METRIC_KEYS[(idx + 1) % len(self.METRIC_KEYS)]
        # Avoid same metric on both axes
        if self.x_metric == self.y_metric:
            self.x_metric = self.METRIC_KEYS[(idx + 2) % len(self.METRIC_KEYS)]
        self._render_plot()
        self.notify(f"X axis: {VISUALIZATION_METRICS[self.x_metric][0]}", timeout=2)

    def action_cycle_y(self) -> None:
        """Cycle to next Y metric."""
        idx = self.METRIC_KEYS.index(self.y_metric)
        self.y_metric = self.METRIC_KEYS[(idx + 1) % len(self.METRIC_KEYS)]
        # Avoid same metric on both axes
        if self.y_metric == self.x_metric:
            self.y_metric = self.METRIC_KEYS[(idx + 2) % len(self.METRIC_KEYS)]
        self._render_plot()
        self.notify(f"Y axis: {VISUALIZATION_METRICS[self.y_metric][0]}", timeout=2)


class CacheManagementScreen(ModalScreen):
    """Modal for managing cache and viewing universe refresh status."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("r", "refresh_selected", "Refresh Selected"),
        Binding("a", "refresh_all", "Refresh All"),
    ]

    CSS = """
    CacheManagementScreen {
        align: center middle;
    }

    #cache-container {
        width: 90;
        height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #cache-title {
        text-align: center;
        text-style: bold;
        color: $secondary;
        padding-bottom: 1;
    }

    #cache-status {
        height: auto;
        padding: 1;
        background: $surface-darken-1;
        margin-bottom: 1;
    }

    #refresh-progress {
        height: auto;
        padding: 1;
        background: $warning-darken-3;
        margin-bottom: 1;
        display: none;
    }

    #refresh-progress.active {
        display: block;
    }

    #progress-bar-container {
        height: 1;
        background: $surface-darken-2;
        margin: 1 0;
    }

    #progress-bar {
        height: 1;
        background: $success;
    }

    #cache-table {
        height: 1fr;
    }

    #cache-footer {
        height: auto;
        padding-top: 1;
        border-top: solid $primary;
    }

    #cache-buttons {
        height: auto;
        padding: 1 0;
    }

    .cache-button {
        margin: 0 1;
    }
    """

    # Polling interval in seconds
    POLL_INTERVAL = 2.0

    def __init__(self, remote_provider: RemoteDataProvider) -> None:
        super().__init__()
        self.remote_provider = remote_provider
        self.universe_stats: list[dict] = []
        self.refresh_status: dict = {}
        self.health_info: dict = {}
        self._poll_timer = None
        self._is_polling = False

    def compose(self) -> ComposeResult:
        with Container(id="cache-container"):
            yield Static("[bold cyan]Cache Manager[/]", id="cache-title")
            yield Static("Loading...", id="cache-status")
            with Container(id="refresh-progress"):
                yield Static("", id="progress-text")
                with Container(id="progress-bar-container"):
                    yield Static("", id="progress-bar")
                yield Static("", id="progress-details")
            yield DataTable(id="cache-table")
            with Container(id="cache-footer"):
                yield Static(
                    "[dim]Select universe and press [green]r[/] to refresh, "
                    "[green]a[/] to refresh all, [green]Esc[/] to close[/]"
                )
                with Horizontal(id="cache-buttons"):
                    yield Button("Refresh Selected", id="btn-refresh", variant="primary", classes="cache-button")
                    yield Button("Refresh All US", id="btn-refresh-us", variant="warning", classes="cache-button")
                    yield Button("Clear Cache", id="btn-clear", variant="error", classes="cache-button")

    def on_mount(self) -> None:
        """Load cache data when mounted."""
        self._setup_table()
        self.run_worker(self._load_cache_data())

    def on_unmount(self) -> None:
        """Clean up timer when unmounted."""
        self._stop_polling()

    def _start_polling(self) -> None:
        """Start polling for refresh status updates."""
        if not self._is_polling:
            self._is_polling = True
            self._poll_timer = self.set_interval(self.POLL_INTERVAL, self._poll_refresh_status)

    def _stop_polling(self) -> None:
        """Stop polling for refresh status updates."""
        self._is_polling = False
        if self._poll_timer:
            self._poll_timer.stop()
            self._poll_timer = None

    def _poll_refresh_status(self) -> None:
        """Poll for refresh status updates."""
        self.run_worker(self._fetch_refresh_status())

    async def _fetch_refresh_status(self) -> None:
        """Fetch just the refresh status (lightweight poll)."""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            self.refresh_status = await loop.run_in_executor(
                None, self.remote_provider.get_refresh_status
            )
            self._update_progress_display()

            # Stop polling if refresh completed
            if not self.refresh_status.get("is_running"):
                self._stop_polling()
                # Reload full data to update cache stats
                self.run_worker(self._load_cache_data())
        except Exception:
            pass  # Silently ignore polling errors

    def _setup_table(self) -> None:
        """Set up the data table columns."""
        table = self.query_one("#cache-table", DataTable)
        table.cursor_type = "row"
        table.add_columns(
            "Universe",
            "Description",
            "Total",
            "Cached",
            "Missing",
            "Coverage",
            "Est. Refresh",
        )

    async def _load_cache_data(self) -> None:
        """Load cache statistics from the API."""
        try:
            # Fetch data in parallel
            import asyncio

            def get_universe_stats():
                return self.remote_provider.get_universe_stats()

            def get_refresh_status():
                return self.remote_provider.get_refresh_status()

            def get_health():
                return self.remote_provider.get_refresh_health()

            # Run sync calls in thread pool
            loop = asyncio.get_event_loop()
            self.universe_stats, self.refresh_status, self.health_info = await asyncio.gather(
                loop.run_in_executor(None, get_universe_stats),
                loop.run_in_executor(None, get_refresh_status),
                loop.run_in_executor(None, get_health),
            )

            self._update_display()

            # Start polling if a refresh is running
            if self.refresh_status.get("is_running"):
                self._start_polling()
        except Exception as e:
            status = self.query_one("#cache-status", Static)
            status.update(f"[red]Error loading cache data: {e}[/]")

    def _update_progress_display(self) -> None:
        """Update just the progress section (for real-time updates)."""
        progress_container = self.query_one("#refresh-progress", Container)

        if self.refresh_status.get("is_running"):
            progress_container.add_class("active")

            universe = self.refresh_status.get("current_universe", "?")
            progress = self.refresh_status.get("progress", {})
            completed = progress.get("completed", 0)
            total = progress.get("total", 1)
            fetched = progress.get("fetched", 0)
            failed = progress.get("failed", 0)

            # Calculate percentage
            pct = (completed / total * 100) if total > 0 else 0

            # Update progress text
            progress_text = self.query_one("#progress-text", Static)
            progress_text.update(
                f"[yellow bold]⟳ REFRESHING:[/] [cyan]{universe}[/] - "
                f"[white]{completed}[/]/[white]{total}[/] ([green]{pct:.0f}%[/])"
            )

            # Update progress bar width
            progress_bar = self.query_one("#progress-bar", Static)
            bar_width = int(pct * 0.84)  # Scale to container width (~84 chars)
            progress_bar.styles.width = max(1, bar_width)

            # Update details
            progress_details = self.query_one("#progress-details", Static)
            eta_seconds = (total - completed) * 2  # Assume 2s per stock
            eta_display = f"{eta_seconds // 60}m {eta_seconds % 60}s" if eta_seconds > 60 else f"{eta_seconds}s"
            progress_details.update(
                f"[green]✓ {fetched} fetched[/]  "
                f"[red]✗ {failed} failed[/]  "
                f"[dim]ETA: ~{eta_display}[/]"
            )
        else:
            progress_container.remove_class("active")

    def _update_display(self) -> None:
        """Update the display with loaded data."""
        # Update status panel
        status = self.query_one("#cache-status", Static)
        status_lines = []

        # Show scheduler info
        scheduler = self.health_info.get("scheduler", {})
        if scheduler.get("enabled"):
            schedule = scheduler.get("schedule_display", "Unknown")
            status_lines.append(f"[green]⏰ Scheduled:[/] {schedule}")
        else:
            status_lines.append("[yellow]⏰ Scheduled refresh: Disabled[/]")

        # Show next refresh
        next_refresh = self.health_info.get("next_scheduled_refresh")
        if next_refresh:
            # Parse and format the time
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(next_refresh.replace("Z", "+00:00"))
                formatted = dt.strftime("%Y-%m-%d %H:%M UTC")
                status_lines.append(f"[cyan]⏭ Next refresh:[/] {formatted}")
            except Exception:
                status_lines.append(f"[cyan]⏭ Next refresh:[/] {next_refresh}")
        else:
            status_lines.append("[dim]⏭ Next refresh: Not scheduled[/]")

        # Show last refresh
        last_refresh = self.health_info.get("last_refresh")
        last_stats = self.health_info.get("last_refresh_stats")
        if last_refresh:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(last_refresh.replace("Z", "+00:00"))
                formatted = dt.strftime("%Y-%m-%d %H:%M UTC")
                last_line = f"[dim]⏮ Last refresh:[/] {formatted}"
                if last_stats:
                    last_universe = last_stats.get("universe", "")
                    last_fetched = last_stats.get("fetched", 0)
                    last_failed = last_stats.get("failed", 0)
                    last_line += f" ({last_universe}: {last_fetched}✓ {last_failed}✗)"
                status_lines.append(last_line)
            except Exception:
                status_lines.append(f"[dim]⏮ Last refresh:[/] {last_refresh}")

        # Show cache stats summary
        cache_stats = self.health_info.get("cache_stats", {})
        if cache_stats:
            total = cache_stats.get("total_stocks", 0)
            status_lines.append(f"[dim]📊 Total cached stocks:[/] {total}")

        status.update("\n".join(status_lines))

        # Update progress display
        self._update_progress_display()

        # Update table
        table = self.query_one("#cache-table", DataTable)
        table.clear()

        for u in self.universe_stats:
            name = u.get("name", "?")
            desc = u.get("description", "")
            # Truncate long descriptions
            if len(desc) > 35:
                desc = desc[:33] + ".."

            total = u.get("total", 0)
            cached = u.get("cached", 0)
            missing = u.get("missing", 0)

            # Calculate coverage percentage
            coverage_pct = (cached / total * 100) if total > 0 else 0
            if coverage_pct >= 90:
                coverage = f"[green]{coverage_pct:.0f}%[/]"
            elif coverage_pct >= 50:
                coverage = f"[yellow]{coverage_pct:.0f}%[/]"
            else:
                coverage = f"[red]{coverage_pct:.0f}%[/]"

            # Mark currently refreshing universe
            if self.refresh_status.get("is_running") and self.refresh_status.get("current_universe") == name:
                name = f"[yellow bold]⟳ {name}[/]"

            est_minutes = u.get("est_refresh_minutes", 0)

            table.add_row(
                name,
                desc,
                str(total),
                str(cached),
                str(missing),
                coverage,
                f"{est_minutes:.1f}m",
                key=u.get("name", "?"),  # Use original name as key
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-refresh":
            self._trigger_refresh_selected()
        elif button_id == "btn-refresh-us":
            self._trigger_refresh_us()
        elif button_id == "btn-clear":
            self._clear_cache()

    def action_refresh_selected(self) -> None:
        """Refresh the selected universe."""
        self._trigger_refresh_selected()

    def action_refresh_all(self) -> None:
        """Refresh all US universes."""
        self._trigger_refresh_us()

    def _trigger_refresh_selected(self) -> None:
        """Trigger refresh for selected universe."""
        table = self.query_one("#cache-table", DataTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key = table.get_row_at(table.cursor_row)
            universe = row_key[0] if row_key else None
            # Strip any markup from universe name
            if universe and "⟳" in universe:
                import re
                universe = re.sub(r'\[.*?\]', '', universe).strip().replace("⟳", "").strip()

            if universe:
                self.notify(f"Triggering refresh for {universe}...", severity="information")
                self.run_worker(self._do_trigger_refresh(universe), exclusive=True, thread=True)

    def _do_trigger_refresh(self, universe: str) -> None:
        """Worker to trigger refresh for a universe."""
        result = self.remote_provider.trigger_refresh(universe)
        if "error" in result:
            self.app.call_from_thread(self.notify, f"Error: {result['error']}", severity="error")
        else:
            est = result.get("estimated_duration_minutes", 0)
            self.app.call_from_thread(self.notify, f"Refresh started for {universe} (~{est:.0f}m)", severity="information")
            # Start polling for real-time updates
            self.app.call_from_thread(self._start_polling)
            # Reload data after triggering (must use call_from_thread since we're in a worker)
            self.app.call_from_thread(lambda: self.run_worker(self._load_cache_data()))

    def _trigger_refresh_us(self) -> None:
        """Trigger refresh for all US universes."""
        self.notify("Triggering refresh for US universes...", severity="information")
        self.run_worker(self._do_trigger_refresh_us(), exclusive=True, thread=True)

    def _do_trigger_refresh_us(self) -> None:
        """Worker to trigger refresh for all US universes."""
        us_universes = ["dow30", "nasdaq100", "sp500"]
        triggered = []

        for universe in us_universes:
            result = self.remote_provider.trigger_refresh(universe)
            if "error" not in result:
                triggered.append(universe)
            else:
                # If one fails (likely already running), stop
                self.app.call_from_thread(
                    self.notify,
                    f"Could not start all: {result.get('error', 'Unknown')}",
                    severity="warning"
                )
                break

        if triggered:
            self.app.call_from_thread(
                self.notify,
                f"Triggered refresh for: {', '.join(triggered)}",
                severity="information"
            )
            # Start polling for real-time updates
            self.app.call_from_thread(self._start_polling)
            # Reload data after triggering (must use call_from_thread since we're in a worker)
            self.app.call_from_thread(lambda: self.run_worker(self._load_cache_data()))

    def _clear_cache(self) -> None:
        """Clear all cached data."""
        self.notify("Clearing cache...", severity="information")
        self.run_worker(self._do_clear_cache(), exclusive=True, thread=True)

    def _do_clear_cache(self) -> None:
        """Worker to clear all cached data."""
        count = self.remote_provider.clear_cache()
        self.app.call_from_thread(self.notify, f"Cleared {count} cached entries", severity="warning")
        # Reload data after clearing (must use call_from_thread since we're in a worker)
        self.app.call_from_thread(lambda: self.run_worker(self._load_cache_data()))


def _truncate_sector(sector: str) -> str:
    """Truncate sector name for compact display."""
    sec = sector
    sec = sec.replace("Communication Services", "Comm Services")
    sec = sec.replace("Consumer Cyclical", "Consumer Cyc")
    sec = sec.replace("Consumer Defensive", "Consumer Def")
    sec = sec.replace("Financial Services", "Financial")
    if len(sec) > 16:
        sec = sec[:14] + ".."
    return sec


class StockDetailScreen(Screen):
    """Screen showing detailed stock analysis."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("w", "add_to_watchlist", "Add to Watchlist"),
        Binding("l", "add_to_long", "Add to Long"),
        Binding("x", "add_to_short", "Add to Short"),
        Binding("d", "deep_research", "Deep Research"),
        Binding("q", "quarterly_data", "Quarterly"),
        Binding("m", "find_similar", "More Like This"),
    ]

    def __init__(self, stock: Stock, remote_provider: RemoteDataProvider) -> None:
        super().__init__()
        self.stock = stock
        self.remote_provider = remote_provider
        self.research_report = None
        self.quarterly_data = None
        self.similar_stocks = None

    def compose(self) -> ComposeResult:
        yield Header()

        # Determine if this is an ETF or stock
        is_etf = getattr(self.stock, "asset_type", "stock") == "etf"

        if is_etf:
            # ETF-specific layout
            subtitle = f"[dim]{self.stock.sector or 'Unknown Category'} | {self.stock.etf.fund_family or 'Unknown Issuer'}[/]"
            yield Container(
                Static(f"[bold cyan]{self.stock.ticker}[/] - {self.stock.name or 'N/A'} [yellow](ETF)[/]", id="stock-title"),
                Static(subtitle, id="stock-subtitle"),
                Horizontal(
                    self._create_panel("Price & Signal", self._get_etf_price_info()),
                    self._create_panel("Fund Info", self._get_etf_fund_info()),
                    self._create_panel("Costs & Fees", self._get_etf_costs_info()),
                    id="top-panels",
                ),
                Horizontal(
                    self._create_panel("Performance", self._get_etf_performance_info()),
                    self._create_panel("Technical", self._get_technical_info()),
                    self._create_panel("Distributions", self._get_dividend_info()),
                    id="bottom-panels",
                ),
                Static("", id="quarterly-panel"),
                Static("", id="similar-panel"),
                Static("", id="research-panel"),
                id="detail-container",
            )
        else:
            # Stock-specific layout (original)
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
                    self._create_panel("Dividends", self._get_dividend_info()),
                    self._create_panel("Buyback Potential", self._get_buyback_info()),
                    id="income-panels",
                ),
                Static("", id="quarterly-panel"),
                Static("", id="similar-panel"),
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

    def _get_dividend_info(self) -> str:
        d = self.stock.dividends
        yield_pct = d.dividend_yield  # Already stored as percentage
        payout = d.payout_ratio

        # Check if this is a dividend-paying stock/ETF
        has_dividend = yield_pct is not None and yield_pct > 0

        if not has_dividend:
            return "[dim]No dividend/distribution[/]"

        # Color code based on yield quality
        if yield_pct:
            if yield_pct >= 4:
                yield_color = "bold green"
            elif yield_pct >= 2:
                yield_color = "green"
            elif yield_pct >= 1:
                yield_color = "yellow"
            else:
                yield_color = "dim"
        else:
            yield_color = "dim"

        # Color code payout ratio (sustainability)
        if payout:
            if payout < 50:
                payout_color = "green"
            elif payout < 75:
                payout_color = "yellow"
            elif payout < 100:
                payout_color = "orange3"
            else:
                payout_color = "red"
        else:
            payout_color = "dim"

        # Core dividend info
        lines = [
            f"Yield: [{yield_color}]{yield_pct:.2f}%[/]" if yield_pct else "Yield: N/A",
            f"Annual Rate: ${d.dividend_rate:.2f}/share" if d.dividend_rate else "Annual Rate: N/A",
        ]

        # Payout ratio
        if payout is not None:
            lines.append(f"Payout Ratio: [{payout_color}]{payout:.0f}%[/]")

        # Frequency
        if d.dividend_frequency:
            lines.append(f"Frequency: {d.dividend_frequency.capitalize()}")

        # Last dividend payment
        if d.last_dividend_value:
            last_div_str = f"${d.last_dividend_value:.4f}"
            if d.last_dividend_date:
                last_div_str += f" ({d.last_dividend_date})"
            lines.append(f"Last Payment: {last_div_str}")

        # Ex-dividend date
        if d.ex_dividend_date:
            lines.append(f"Ex-Dividend: {d.ex_dividend_date}")

        lines.append("")

        # Historical context
        if d.trailing_annual_dividend_rate:
            lines.append(f"Trailing 12M: ${d.trailing_annual_dividend_rate:.2f}/share")

        if d.five_year_avg_dividend_yield:
            # Compare current yield to 5-year average
            if yield_pct and d.five_year_avg_dividend_yield > 0:
                vs_avg = ((yield_pct / d.five_year_avg_dividend_yield) - 1) * 100
                avg_color = "green" if vs_avg > 10 else "yellow" if vs_avg > -10 else "red"
                lines.append(f"5Y Avg Yield: {d.five_year_avg_dividend_yield:.2f}% ([{avg_color}]{vs_avg:+.0f}%[/] vs now)")
            else:
                lines.append(f"5Y Avg Yield: {d.five_year_avg_dividend_yield:.2f}%")

        # Add contextual narrative
        if yield_pct and yield_pct >= 4:
            lines.append("")
            lines.append("[green]High yield income opportunity.[/]")
            if payout and payout > 80:
                lines.append("[yellow]Watch payout sustainability.[/]")

        return "\n".join(lines)

    def _fmt(self, val) -> str:
        return f"{val:.2f}" if val is not None else "N/A"

    def _pct(self, val) -> str:
        return f"{val:+.1f}%" if val is not None else "N/A"

    def _get_etf_fund_info(self) -> str:
        """Get ETF fund information panel content."""
        e = self.stock.etf

        # Format AUM
        aum_str = "N/A"
        if e.aum:
            if e.aum >= 1_000_000_000:
                aum_str = f"${e.aum / 1_000_000_000:.1f}B"
            elif e.aum >= 1_000_000:
                aum_str = f"${e.aum / 1_000_000:.0f}M"
            else:
                aum_str = f"${e.aum / 1_000:.0f}K"

        # Color code AUM (larger = more liquid)
        aum_color = "green" if e.aum and e.aum > 1_000_000_000 else "yellow" if e.aum and e.aum > 100_000_000 else "red" if e.aum else "dim"

        lines = [
            f"Fund Family: [cyan]{e.fund_family or 'N/A'}[/]",
            f"Category: {e.category or 'N/A'}",
            f"AUM: [{aum_color}]{aum_str}[/]",
            f"Holdings: {e.holdings_count or 'N/A'}",
            f"Inception: {e.inception_date or 'N/A'}",
            "",
            "[dim]Larger AUM = more liquid.",
            "More holdings = more",
            "diversification. Older funds",
            "have longer track records.[/]",
        ]
        return "\n".join(lines)

    def _get_etf_costs_info(self) -> str:
        """Get ETF costs and fees panel content."""
        e = self.stock.etf

        # Expense ratio color coding
        exp_color = "green" if e.expense_ratio is not None and e.expense_ratio < 0.10 else \
                    "yellow" if e.expense_ratio is not None and e.expense_ratio < 0.50 else \
                    "red" if e.expense_ratio is not None else "dim"
        exp_str = f"{e.expense_ratio:.2f}%" if e.expense_ratio is not None else "N/A"

        # Premium/discount color coding
        prem_disc = e.premium_discount
        prem_color = "green" if prem_disc is not None and abs(prem_disc) < 0.1 else \
                     "yellow" if prem_disc is not None and abs(prem_disc) < 0.5 else \
                     "red" if prem_disc is not None else "dim"
        prem_str = f"{prem_disc:+.2f}%" if prem_disc is not None else "N/A"

        # NAV
        nav_str = f"${e.nav:.2f}" if e.nav else "N/A"

        lines = [
            f"Expense Ratio: [{exp_color}]{exp_str}[/]",
            f"NAV: {nav_str}",
            f"Premium/Disc: [{prem_color}]{prem_str}[/]",
            "",
            "[dim]Lower expense = more of",
            "your returns kept. Premium",
            "means paying above NAV.",
            "Discount = buying below NAV.[/]",
        ]

        # Cost comparison context
        if e.expense_ratio is not None:
            if e.expense_ratio < 0.05:
                lines.append("")
                lines.append("[green]Ultra-low cost fund.[/]")
            elif e.expense_ratio < 0.20:
                lines.append("")
                lines.append("[yellow]Competitive expense ratio.[/]")
            elif e.expense_ratio > 0.75:
                lines.append("")
                lines.append("[red]High cost - consider alternatives.[/]")

        return "\n".join(lines)

    def _get_etf_performance_info(self) -> str:
        """Get ETF performance panel content."""
        e = self.stock.etf
        t = self.stock.technical

        # YTD Return
        ytd_color = "green" if e.ytd_return and e.ytd_return > 0 else "red" if e.ytd_return else "dim"
        ytd_str = f"{e.ytd_return:+.1f}%" if e.ytd_return is not None else "N/A"

        # 1Y Return (from technical)
        ret_1y = t.return_1y
        ret_1y_color = "green" if ret_1y and ret_1y > 0 else "red" if ret_1y else "dim"
        ret_1y_str = f"{ret_1y:+.1f}%" if ret_1y is not None else "N/A"

        # 3Y Return
        ret_3y_color = "green" if e.return_3y and e.return_3y > 0 else "red" if e.return_3y else "dim"
        ret_3y_str = f"{e.return_3y:+.1f}%" if e.return_3y is not None else "N/A"

        # 5Y Return
        ret_5y_color = "green" if e.return_5y and e.return_5y > 0 else "red" if e.return_5y else "dim"
        ret_5y_str = f"{e.return_5y:+.1f}%" if e.return_5y is not None else "N/A"

        # Beta
        beta_str = f"{e.beta_3y:.2f}" if e.beta_3y is not None else "N/A"
        beta_color = "yellow" if e.beta_3y and e.beta_3y > 1.2 else "green" if e.beta_3y else "dim"

        lines = [
            f"YTD: [{ytd_color}]{ytd_str}[/]",
            f"1 Year: [{ret_1y_color}]{ret_1y_str}[/]",
            f"3 Year (ann): [{ret_3y_color}]{ret_3y_str}[/]",
            f"5 Year (ann): [{ret_5y_color}]{ret_5y_str}[/]",
            f"Beta (3Y): [{beta_color}]{beta_str}[/]",
            "",
            "[dim]Multi-year returns show",
            "consistency. Beta>1 means",
            "more volatile than market.[/]",
        ]
        return "\n".join(lines)

    def _get_etf_price_info(self) -> str:
        """Get ETF price and signal panel content."""
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

        # ETF-specific signal descriptions
        signal_desc = {
            "STRONG_BUY": "Low-cost fund with strong oversold signals - potential opportunity.",
            "BUY": "Low expense ratio with oversold technicals worth investigating.",
            "WATCH": "Good cost structure approaching oversold territory.",
            "NEUTRAL": "Low-cost fund with no strong technical signals.",
            "NO_SIGNAL": "Either high cost or insufficient data.",
        }.get(signal, "")

        lines = [
            f"Price: [bold]{price}[/]",
            f"Signal: [{signal_color}]{signal}[/]",
            "",
            f"[dim]{signal_desc}[/]",
        ]
        return "\n".join(lines)

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

        try:
            report = deep_research(self.stock.ticker)
            self.call_from_thread(self._display_research, report)
        except Exception:
            # Screen may have been dismissed, silently ignore
            pass

    def _display_research(self, report) -> None:
        """Display research report in the panel."""
        try:
            research_panel = self.query_one("#research-panel", Static)
        except Exception:
            # Screen was dismissed before callback ran
            return

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

        try:
            trends = fetch_quarterly_financials(self.stock.ticker, periods=8)
            self.call_from_thread(self._display_quarterly, trends)
        except Exception:
            # Screen may have been dismissed, silently ignore
            pass

    def _display_quarterly(self, trends) -> None:
        """Display quarterly trends in the panel."""
        from tradfi.utils.sparkline import format_large_number, sparkline

        try:
            quarterly_panel = self.query_one("#quarterly-panel", Static)
        except Exception:
            # Screen was dismissed before callback ran
            return

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

    def action_find_similar(self) -> None:
        """Find stocks similar to the current stock."""
        similar_panel = self.query_one("#similar-panel", Static)
        similar_panel.update(
            "[bold yellow]More Like This[/]\n\n"
            f"[dim]Finding stocks similar to {self.stock.ticker}...[/]"
        )

        # Run in background thread
        self.run_worker(self._fetch_similar, thread=True)

    def _fetch_similar(self) -> None:
        """Background worker to find similar stocks."""
        try:
            # Fetch all stocks from cache to compare against
            all_tickers = []
            for name in AVAILABLE_UNIVERSES.keys():
                try:
                    all_tickers.extend(load_tickers(name))
                except FileNotFoundError:
                    pass

            # Remove duplicates and limit to reasonable size
            unique_tickers = list(set(all_tickers))

            # Fetch stock data in batch
            all_stocks = self.remote_provider.fetch_stocks_batch(unique_tickers)
            candidates = list(all_stocks.values())

            # Find similar stocks
            similar = find_similar_stocks(self.stock, candidates, limit=8, min_score=20)

            self.call_from_thread(self._display_similar, similar)
        except Exception:
            # Screen may have been dismissed, silently ignore
            pass

    def _display_similar(self, similar: list) -> None:
        """Display similar stocks in the panel."""
        try:
            similar_panel = self.query_one("#similar-panel", Static)
        except Exception:
            # Screen was dismissed before callback ran
            return

        if not similar:
            similar_panel.update(
                "[bold cyan]More Like This[/]\n\n"
                "[dim]No similar stocks found in the universe.[/]"
            )
            return

        lines = [
            f"[bold cyan]More Like This[/] [dim]({len(similar)} similar stocks)[/]",
            "",
            "[dim]Ticker   Score  P/E    ROE    RSI  Why[/]",
        ]

        for stock, score, reasons in similar:
            ticker = f"{stock.ticker:<8}"
            score_str = f"{score:.0f}"

            pe = stock.valuation.pe_trailing
            pe_str = f"{pe:.1f}" if pe and isinstance(pe, (int, float)) and pe > 0 else "-"

            roe = stock.profitability.roe
            roe_str = f"{roe:.0f}%" if roe else "-"

            rsi = stock.technical.rsi_14
            rsi_str = f"{rsi:.0f}" if rsi else "-"

            reason_str = ", ".join(reasons[:3]) if reasons else ""

            # Color code by score
            if score >= 60:
                score_color = "green"
            elif score >= 40:
                score_color = "yellow"
            else:
                score_color = "dim"

            lines.append(
                f"{ticker} [{score_color}]{score_str:>3}[/]    "
                f"{pe_str:>5}  {roe_str:>5}  {rsi_str:>3}  [dim]{reason_str}[/]"
            )

        lines.append("")
        lines.append("[dim]Similar based on: industry, size, valuation,[/]")
        lines.append("[dim]profitability, dividend, and momentum.[/]")

        similar_panel.update("\n".join(lines))


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

    #sector-select {
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

    #sector-search {
        height: 1;
        min-height: 1;
        padding: 0 1;
        margin: 0 0 1 0;
        border: none;
        background: $surface-darken-1;
    }

    #sector-search:focus {
        border: solid $accent;
    }

    #sort-indicator {
        width: auto;
        padding: 0 2;
        text-align: center;
    }

    #currency-indicator {
        width: auto;
        padding: 0 2;
        text-align: center;
    }
    """

    # Simplified bindings - most actions now in action menu (Space)
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("space", "show_actions", "Actions", show=True, priority=True),
        Binding("enter", "select", "Select", show=False),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("/", "focus_search", "Search", show=True),
        Binding("escape", "back", "Back", show=True),
        Binding("?", "help", "Help", show=False),
        # Keep sort keys for power users but hide from footer
        Binding("s", "save_list", "Save List", show=False),
        Binding("u", "focus_universe", "Filter Universe", show=False),
        Binding("f", "focus_sector", "Filter Sector", show=False),
        Binding("c", "clear_filters", "Clear Filters", show=False),
        Binding("1", "sort_ticker", "Sort: Ticker", show=False),
        Binding("i", "sort_sector", "Sort: Sector", show=False),
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
        Binding("$", "toggle_currency", "Currency", show=False),
        Binding("K", "cache_manage", "Cache Manager", show=False),
    ]

    # Sort options: (attribute_getter, reverse_default, display_name)
    # reverse_default=True means higher values first by default
    SORT_OPTIONS = {
        "ticker": (lambda s: s.ticker, False, "Ticker"),
        "sector": (lambda s: s.sector or "ZZZ", False, "Sector"),
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
        # ETF-specific sort options
        "exp": (lambda s: s.etf.expense_ratio if s.etf.expense_ratio is not None else float("inf"), False, "ExpRatio"),
        "aum": (lambda s: s.etf.aum if s.etf.aum else 0, True, "AUM"),
        "ytd": (lambda s: s.etf.ytd_return if s.etf.ytd_return is not None else float("-inf"), True, "YTD"),
    }

    def __init__(self, api_url: str) -> None:
        super().__init__()
        self.current_preset = None
        self.stocks: list[Stock] = []
        self.sectors: dict[str, list[Stock]] = {}
        self.current_sort = "pe"  # Default sort
        self.sort_reverse = False  # Toggle for ascending/descending
        self._viewing_list: str | None = None  # Track if viewing a position list (display name)
        self._viewing_list_name: str | None = None  # Track actual list name (e.g., "_long")
        self._portfolio_mode: bool = False  # Track if viewing portfolio P&L mode
        self.selected_sectors: set[str] = set()  # Selected sectors (include)
        self.selected_universes: set[str] = set()  # Selected universes
        self.selected_categories: set[str] = set()  # Selected categories (for ETF universe)
        self._sectors_loaded: bool = False  # Track if sectors list is populated
        self._all_sectors: list[tuple[str, int]] = []  # Full list for filtering

        # Remote API provider (required - TUI always uses remote API)
        self.api_url = api_url
        self.remote_provider = RemoteDataProvider(api_url)

        # Currency display settings
        from tradfi.core.currency import DEFAULT_CURRENCY_CYCLE
        from tradfi.utils.cache import get_display_currency
        self._currency_cycle = DEFAULT_CURRENCY_CYCLE
        self._display_currency = get_display_currency()  # Load from config

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
                Static("Universes [dim](toggle)[/]", classes="section-title", id="universe-title"),
                SelectionList[str](id="universe-select"),
                Static("Categories", classes="section-title", id="category-title"),
                SelectionList[str](id="category-select"),
                Static("Sectors [dim](toggle)[/]", classes="section-title", id="sector-title"),
                Input(placeholder="Filter sectors...", id="sector-search"),
                SelectionList[str](id="sector-select"),
                Static("Presets", classes="section-title"),
                OptionList(
                    "[dim]None (Custom)[/]",
                    *[
                        f"[bold]{PRESET_INFO[k]['name']}[/] [dim]{PRESET_INFO[k]['criteria']}[/]"
                        for k in PRESET_SCREENS.keys()
                    ],
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
                FilterPillsContainer(id="filter-pills"),
                DataTable(id="results-table"),
                id="content",
            ),
            id="main-container",
        )
        yield Horizontal(
            Static("[dim]Ready.[/] Press [bold]Space[/] for actions, [bold]/[/] to search, [bold]r[/] to scan.", id="status-bar"),
            Static("[cyan]Sort: P/E ↓[/]", id="sort-indicator"),
            Static(f"[yellow]{self._display_currency}[/]", id="currency-indicator"),
            Static("[dim]Connecting...[/]", id="api-status"),
            id="bottom-bar",
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.display = False
        table.cursor_type = "row"
        # Simplified columns for cleaner view (9 instead of 14)
        # Focus on key value metrics: Ticker, Sector, Price, P/E, ROE, RSI, MoS%, Div, Signal
        table.add_columns("Company", "Sector", "Price", "P/E", "ROE", "RSI", "MoS%", "Div", "Signal")

        # Populate universe selection list
        self._populate_universes()

        # Set initial filter section visibility (default: show Sectors)
        self._update_filter_section_visibility()

        # Populate sector selection list in background (avoid blocking startup)
        self.run_worker(self._fetch_sectors_async, thread=True)

        # Fetch API status in background
        self.run_worker(self._fetch_api_status, thread=True)

    def _fetch_sectors_async(self) -> list[tuple[str, int]] | None:
        """Fetch sectors from API in background thread."""
        try:
            return self.remote_provider.get_sectors(None)
        except Exception:
            return None

    def _update_sectors_ui(self, sectors: list[tuple[str, int]]) -> None:
        """Update sector UI with fetched data."""
        try:
            sector_select = self.query_one("#sector-select", SelectionList)

            # Store full list for filtering
            self._all_sectors = sorted(sectors, key=lambda x: x[0].lower())

            # Clear any previously selected sectors that are no longer available
            available_sectors = {sec for sec, _ in sectors}
            self.selected_sectors = self.selected_sectors & available_sectors

            # Display all sectors
            self._display_filtered_sectors("")

            self._sectors_loaded = True
        except Exception:
            pass

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

    def _populate_sectors(self, tickers: list[str] | None = None) -> None:
        """Populate the sector selection list from remote API.

        Args:
            tickers: Optional list of tickers to filter sectors by.
                     If not provided, shows all sectors from cache.
        """
        # Run the blocking API call in a worker thread
        self.run_worker(lambda: self._fetch_and_populate_sectors(tickers), exclusive=True, thread=True)

    def _fetch_and_populate_sectors(self, tickers: list[str] | None = None) -> None:
        """Worker to fetch sectors and update UI."""
        try:
            # Get sectors from remote API (filtered by tickers if provided)
            sectors = self.remote_provider.get_sectors(tickers)

            # Update UI on main thread
            self.call_from_thread(self._apply_sectors_to_ui, sectors)
        except Exception:
            pass

    def _apply_sectors_to_ui(self, sectors: list[tuple[str, int]] | None) -> None:
        """Apply fetched sectors to the UI (must run on main thread)."""
        try:
            sector_select = self.query_one("#sector-select", SelectionList)

            if not sectors:
                sector_select.clear_options()
                sector_select.add_option(("No cached data", "none", False))
                return

            # Store full list for filtering
            self._all_sectors = sorted(sectors, key=lambda x: x[0].lower())

            # Clear any previously selected sectors that are no longer available
            available_sectors = {sec for sec, _ in sectors}
            self.selected_sectors = self.selected_sectors & available_sectors

            # Display all sectors
            self._display_filtered_sectors("")

            self._sectors_loaded = True
        except Exception:
            pass

    def _update_sectors_for_selection(self) -> None:
        """Update the sector list based on selected universes."""
        # Get all tickers from selected universes
        tickers: list[str] = []
        universes_to_check = (
            self.selected_universes if self.selected_universes
            else set(AVAILABLE_UNIVERSES.keys())
        )

        for name in universes_to_check:
            try:
                if self.selected_categories:
                    tickers.extend(load_tickers_by_categories(name, self.selected_categories))
                else:
                    tickers.extend(load_tickers(name))
            except FileNotFoundError:
                pass

        # Update sectors with the tickers from selected universes
        self._populate_sectors(tickers if tickers else None)

    def _is_etf_only_selection(self) -> bool:
        """Check if only 'etf' universe is selected.

        Returns:
            True if only 'etf' is selected, False otherwise.
            No selection or mixed universes = False (show Sectors).
        """
        if not self.selected_universes:
            return False  # No selection = show Sectors
        return self.selected_universes == {"etf"}

    def _update_filter_section_visibility(self) -> None:
        """Toggle visibility between Categories and Sectors based on universe selection.

        - ETF only: Show Categories, hide Sectors
        - Stock universes or mixed: Show Sectors, hide Categories
        """
        try:
            is_etf_only = self._is_etf_only_selection()

            # Get UI elements
            category_title = self.query_one("#category-title", Static)
            category_select = self.query_one("#category-select", SelectionList)
            sector_title = self.query_one("#sector-title", Static)
            sector_search = self.query_one("#sector-search", Input)
            sector_select = self.query_one("#sector-select", SelectionList)

            if is_etf_only:
                # Show Categories, hide Sectors
                category_title.styles.display = "block"
                category_select.styles.display = "block"
                sector_title.styles.display = "none"
                sector_search.styles.display = "none"
                sector_select.styles.display = "none"

                # Clear sector selections when hiding
                if self.selected_sectors:
                    sector_select.deselect_all()
                    self.selected_sectors = set()
            else:
                # Show Sectors, hide Categories
                category_title.styles.display = "none"
                category_select.styles.display = "none"
                sector_title.styles.display = "block"
                sector_search.styles.display = "block"
                sector_select.styles.display = "block"

                # Clear category selections when hiding
                if self.selected_categories:
                    category_select.deselect_all()
                    self.selected_categories = set()
        except Exception:
            pass

    def _display_filtered_sectors(self, search_term: str) -> None:
        """Display sectors filtered by search term."""
        try:
            sector_select = self.query_one("#sector-select", SelectionList)

            # Remember current selections
            current_selections = set(sector_select.selected)

            # Clear and repopulate
            sector_select.clear_options()

            # Filter sectors by search term
            search_lower = search_term.lower().strip()
            if search_lower:
                filtered = [
                    (sec, count) for sec, count in self._all_sectors
                    if search_lower in sec.lower()
                ]
            else:
                filtered = self._all_sectors

            if not filtered and search_term:
                sector_select.add_option((f"No matches for '{search_term}'", "__none__", False))
                return

            # Add "ALL" option at the top
            total_stocks = sum(count for _, count in filtered)
            sector_select.add_option((f"★ ALL ({total_stocks})", "__all__", False))

            # Add filtered sectors
            for sector, count in filtered:
                display_name = _truncate_sector(sector)
                label = f"{display_name} ({count})"
                # Restore selection if it was selected before
                is_selected = sector in current_selections
                sector_select.add_option((label, sector, is_selected))

        except Exception:
            pass

    def _get_universes_with_categories(self) -> dict[str, list[str]]:
        """Get all universes that have categories and their category lists."""
        result = {}
        for universe in AVAILABLE_UNIVERSES.keys():
            categories = get_universe_categories(universe)
            if categories:
                result[universe] = categories
        return result

    def _update_categories_for_selection(self) -> None:
        """Update the category list based on selected universes.

        Note: Visibility is handled by _update_filter_section_visibility().
        This method only populates the category options.
        """
        try:
            category_select = self.query_one("#category-select", SelectionList)
            category_title = self.query_one("#category-title", Static)

            # Clear existing options
            category_select.clear_options()
            self.selected_categories = set()

            # Only populate if ETF-only selection
            if not self._is_etf_only_selection():
                return

            # Get universes with categories
            universes_with_cats = self._get_universes_with_categories()

            # Collect all categories from ETF universe
            all_categories = set()
            for universe in self.selected_universes & set(universes_with_cats.keys()):
                all_categories.update(universes_with_cats.get(universe, []))

            if not all_categories:
                category_title.update("Categories [dim](none available)[/]")
                return

            # Update title
            category_title.update("Categories [dim](toggle)[/]")

            # Add "ALL" option at the top
            category_select.add_option(("★ ALL", "__all__", False))

            # Add each category with icon if available
            for cat in sorted(all_categories):
                icon = ETF_CATEGORY_ICONS.get(cat, "")
                display_name = f"{icon} {cat}" if icon else cat
                category_select.add_option((display_name, cat, False))

        except Exception:
            pass

    def _populate_categories(self, universe: str) -> None:
        """Populate the category selection list for a universe (legacy compatibility)."""
        self._update_categories_for_selection()

    def _hide_categories(self) -> None:
        """Update categories when universes change."""
        self._update_categories_for_selection()

    def on_selection_list_selected_changed(self, event: SelectionList.SelectedChanged) -> None:
        """Handle selection changes for universes, categories, and sectors."""
        if event.selection_list.id == "universe-select":
            # Update selected universes (filter out __all__ marker)
            selected = set(event.selection_list.selected)
            if "__all__" in selected:
                self.selected_universes = set()
            else:
                self.selected_universes = selected
            # Toggle visibility between Categories and Sectors
            self._update_filter_section_visibility()
            # Update the visible filter section
            if self._is_etf_only_selection():
                self._update_categories_for_selection()
            else:
                self._update_sectors_for_selection()
            self._update_workflow_status()
            self._update_section_titles()
            self._update_filter_pills()
        elif event.selection_list.id == "category-select":
            # Update selected categories (filter out __all__ marker)
            selected = set(event.selection_list.selected)
            if "__all__" in selected:
                self.selected_categories = set()
            else:
                self.selected_categories = selected
            # Update sectors based on category selection too
            self._update_sectors_for_selection()
            self._update_workflow_status()
            self._update_section_titles()
            self._update_filter_pills()
        elif event.selection_list.id == "sector-select":
            # Update selected sectors (filter out __all__ marker)
            selected = set(event.selection_list.selected)
            if "__all__" in selected:
                self.selected_sectors = set()
            else:
                self.selected_sectors = selected
            self._update_workflow_status()
            self._update_section_titles()
            self._update_filter_pills()

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

        # Build status message with actual names
        parts = []

        # Universe names (show up to 3, then count)
        if self.selected_universes:
            if len(self.selected_universes) <= 3:
                names = sorted(self.selected_universes)
                parts.append(f"[cyan]{'+'.join(names)}[/]")
            else:
                parts.append(f"[cyan]{len(self.selected_universes)} universes[/]")
        else:
            parts.append("[dim]all universes[/]")

        # Category names (show up to 2, then count)
        if self.selected_categories:
            if len(self.selected_categories) <= 2:
                cats = sorted(self.selected_categories)
                parts.append(f"[magenta]{'+'.join(cats)}[/]")
            else:
                parts.append(f"[magenta]{len(self.selected_categories)} categories[/]")

        # Sector names (show up to 2, then count)
        if self.selected_sectors:
            if len(self.selected_sectors) <= 2:
                secs = sorted(self.selected_sectors)
                # Truncate long names
                short_secs = [sec[:15] + ".." if len(sec) > 17 else sec for sec in secs]
                parts.append(f"[yellow]{'+'.join(short_secs)}[/]")
            else:
                parts.append(f"[yellow]{len(self.selected_sectors)} sectors[/]")

        filter_desc = " | ".join(parts)

        # Preset info with criteria
        if self.current_preset and self.current_preset in PRESET_INFO:
            preset_name = PRESET_INFO[self.current_preset]["name"]
            preset_criteria = PRESET_INFO[self.current_preset]["criteria"]
            preset_info = f" [bold green]{preset_name}[/] [dim]({preset_criteria})[/]"
        elif self.current_preset:
            preset_info = f" [bold green]{self.current_preset}[/]"
        else:
            preset_info = ""

        self._update_status(
            f"{filter_desc}{preset_info} [dim]~{total_tickers} stocks[/] | "
            f"[bold]r[/]=scan"
        )

    def _update_section_titles(self) -> None:
        """Update section titles to show selection counts."""
        try:
            # Update universe title
            universe_title = self.query_one("#universe-title", Static)
            if self.selected_universes:
                count = len(self.selected_universes)
                universe_title.update(f"Universes [cyan]({count} selected)[/]")
            else:
                universe_title.update("Universes [dim](toggle)[/]")

            is_etf_only = self._is_etf_only_selection()

            if is_etf_only:
                # Update category title (only when visible)
                category_title = self.query_one("#category-title", Static)
                if self.selected_categories:
                    count = len(self.selected_categories)
                    category_title.update(f"Categories [magenta]({count} selected)[/]")
                else:
                    category_title.update("Categories [dim](toggle)[/]")
            else:
                # Update sector title (only when visible)
                sector_title = self.query_one("#sector-title", Static)
                if self.selected_sectors:
                    count = len(self.selected_sectors)
                    sector_title.update(f"Sectors [yellow]({count} selected)[/]")
                else:
                    sector_title.update("Sectors [dim](toggle)[/]")
        except Exception:
            pass

    def _update_filter_pills(self) -> None:
        """Update the filter pills container based on current filter state."""
        try:
            pills_container = self.query_one("#filter-pills", FilterPillsContainer)
            pills_container.update_pills(
                universes=self.selected_universes,
                sectors=self.selected_sectors,
                categories=self.selected_categories,
                preset=self.current_preset,
            )
        except Exception:
            pass

    def on_filter_pill_removed(self, event: FilterPill.Removed) -> None:
        """Handle removal of a filter pill."""
        filter_type = event.filter_type
        filter_value = event.filter_value

        try:
            if filter_type == "universe":
                # Remove from selected universes and deselect in list
                self.selected_universes.discard(filter_value)
                universe_select = self.query_one("#universe-select", SelectionList)
                universe_select.deselect(filter_value)
                # Toggle visibility and update visible filter section
                self._update_filter_section_visibility()
                if self._is_etf_only_selection():
                    self._update_categories_for_selection()
                else:
                    self._update_sectors_for_selection()
            elif filter_type == "sector":
                # Remove from selected sectors and deselect in list
                self.selected_sectors.discard(filter_value)
                sector_select = self.query_one("#sector-select", SelectionList)
                sector_select.deselect(filter_value)
            elif filter_type == "category":
                # Remove from selected categories and deselect in list
                self.selected_categories.discard(filter_value)
                category_select = self.query_one("#category-select", SelectionList)
                category_select.deselect(filter_value)
            elif filter_type == "preset":
                # Clear preset
                self.current_preset = None
                # Also deselect in preset list
                preset_list = self.query_one("#preset-list", OptionList)
                preset_list.highlighted = 0  # Select "None (Custom)"

            # Update all UI components
            self._update_section_titles()
            self._update_filter_pills()
            self._update_workflow_status()
        except Exception:
            pass

    def on_clear_all_pill_clicked(self, event: ClearAllPill.Clicked) -> None:
        """Handle click on Clear All pill."""
        self.action_clear_filters()

    def _get_preset_key_from_selection(self, selected: str) -> str | None:
        """Extract preset key from the formatted option string."""
        if "None" in selected or "Custom" in selected:
            return None
        # Find which preset matches based on display name
        for key, info in PRESET_INFO.items():
            if info["name"] in selected:
                return key
        return None

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "preset-list":
            selected = str(event.option.prompt)
            self.current_preset = self._get_preset_key_from_selection(selected)
            self._update_filter_pills()
            self._run_screen()
        elif event.option_list.id == "position-list":
            selected = str(event.option.prompt)
            if "Long" in selected:
                self._load_position_list("_long", "Long List")
            elif "Short" in selected:
                self._load_position_list("_short", "Short List")

    def _run_screen(self) -> None:
        # Clear position list view flags - we're now screening
        self._viewing_list = None
        self._viewing_list_name = None
        self._portfolio_mode = False

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
        sector_desc = f" ({len(self.selected_sectors)} sectors)" if self.selected_sectors else ""

        loading_text = self.query_one("#loading-text", Static)
        loading_text.update(f"[cyan]SCANNING {universe_desc.upper()}[/]{preset_desc}{sector_desc}")

        loading_detail = self.query_one("#loading-detail", Static)
        loading_detail.update("[dim]Initializing...[/]")

        loading_stats = self.query_one("#loading-stats", Static)
        loading_stats.update("")

        self.run_worker(self._fetch_stocks, exclusive=True, thread=True)

    def _load_position_list(self, list_name: str, display_name: str) -> None:
        """Load and display a position list (long or short).

        If the list has position data (shares/entry prices), shows portfolio view with P&L.
        Otherwise shows standard stock view.
        """
        list_data = self.remote_provider.get_list(list_name)
        tickers = list_data.get("tickers", []) if list_data else []

        if not tickers:
            self.notify(f"{display_name} is empty.\nAdd stocks with 'l' (long) or 'x' (short) in detail view.",
                       title=display_name, severity="warning", timeout=5)
            return

        # Check if list has portfolio data
        has_positions = self.remote_provider.has_positions(list_name)

        loading = self.query_one("#loading", Container)
        table = self.query_one("#results-table", DataTable)
        loading.display = True
        table.display = False

        loading_text = self.query_one("#loading-text", Static)
        if has_positions:
            loading_text.update(f"[cyan]LOADING PORTFOLIO: {display_name.upper()}[/]")
        else:
            loading_text.update(f"[cyan]LOADING {display_name.upper()}[/]")

        loading_detail = self.query_one("#loading-detail", Static)
        loading_detail.update("[dim]Initializing...[/]")

        loading_stats = self.query_one("#loading-stats", Static)
        loading_stats.update(f"[dim]{len(tickers)} positions[/]")

        # Store which list we're viewing for status bar
        self._viewing_list = display_name
        self._viewing_list_name = list_name
        self._portfolio_mode = has_positions

        if has_positions:
            # Fetch portfolio data with P&L calculations
            self.run_worker(
                lambda: self._fetch_portfolio(list_name),
                exclusive=True,
                thread=True,
                name="_fetch_portfolio"
            )
        else:
            # Standard stock list view
            self.run_worker(
                lambda: self._fetch_position_stocks(tickers),
                exclusive=True,
                thread=True
            )

    def _fetch_portfolio(self, list_name: str) -> dict | None:
        """Fetch portfolio data with P&L calculations."""
        return self.remote_provider.get_portfolio(list_name)

    def _populate_portfolio_table(self, portfolio: dict) -> None:
        """Populate table with portfolio P&L view."""
        loading = self.query_one("#loading", Container)
        table = self.query_one("#results-table", DataTable)

        loading.display = False
        table.display = True

        # Clear and reconfigure columns for portfolio view
        table.clear(columns=True)
        table.add_columns("Ticker", "Shares", "Entry", "Price", "Value", "P&L", "P&L%", "Alloc%")

        items = portfolio.get("items", [])
        for item in items:
            ticker = item.get("ticker", "-")
            shares_val = item.get("shares")
            entry_val = item.get("entry_price")
            price_val = item.get("current_price")
            value_val = item.get("current_value")

            shares = f"{shares_val:.0f}" if shares_val is not None else "-"
            entry = f"${entry_val:.2f}" if entry_val is not None else "-"
            price = f"${price_val:.2f}" if price_val is not None else "-"
            value = f"${value_val:,.0f}" if value_val is not None else "-"

            pnl = item.get("gain_loss")
            pnl_pct = item.get("gain_loss_pct")
            alloc = item.get("allocation_pct")

            # Color P&L based on gain/loss
            if pnl is not None:
                pnl_color = "green" if pnl >= 0 else "red"
                pnl_str = f"[{pnl_color}]${pnl:+,.0f}[/]"
            else:
                pnl_str = "-"

            if pnl_pct is not None:
                pnl_pct_color = "green" if pnl_pct >= 0 else "red"
                pnl_pct_str = f"[{pnl_pct_color}]{pnl_pct:+.1f}%[/]"
            else:
                pnl_pct_str = "-"

            alloc_str = f"{alloc:.1f}%" if alloc is not None else "-"

            table.add_row(ticker, shares, entry, price, value, pnl_str, pnl_pct_str, alloc_str, key=ticker)

        # Update status bar with portfolio summary
        total_cost = portfolio.get("total_cost_basis", 0)
        total_value = portfolio.get("total_current_value", 0)
        total_pnl = portfolio.get("total_gain_loss", 0)
        total_pnl_pct = portfolio.get("total_gain_loss_pct")
        position_count = portfolio.get("position_count", 0)

        pnl_color = "green" if total_pnl >= 0 else "red"
        pnl_pct_display = f" ({total_pnl_pct:+.1f}%)" if total_pnl_pct is not None else ""

        self._update_status(
            f"{self._viewing_list}: {position_count} positions. "
            f"Cost: ${total_cost:,.0f} | Value: ${total_value:,.0f} | "
            f"P&L: [{pnl_color}]${total_pnl:+,.0f}{pnl_pct_display}[/]. "
            f"Enter=details"
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

        # Update progress to show we're fetching
        self.call_from_thread(
            self._update_progress_batch, "Loading from cache...", 0, len(ticker_list), 0
        )

        # Fetch all stocks in a single batch request (MUCH faster than individual requests)
        all_stocks = self.remote_provider.fetch_stocks_batch(ticker_list)

        # Filter stocks locally (fast in-memory operation)
        passing_stocks = []
        total = len(ticker_list)

        for i, ticker in enumerate(ticker_list):
            # Update progress less frequently (every 50 stocks) to reduce UI overhead
            if i % 50 == 0 or i == total - 1:
                found = len(passing_stocks)
                self.call_from_thread(
                    self._update_progress_batch, f"Filtering {ticker}...",
                    i + 1, total, found
                )

            stock = all_stocks.get(ticker)
            if stock:
                # Apply screening criteria
                if not screen_stock(stock, criteria):
                    continue

                # Apply sector filter (if any sectors are selected)
                if self.selected_sectors:
                    if stock.sector not in self.selected_sectors:
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

    def _update_progress_batch(self, status: str, current: int, total: int, found: int) -> None:
        """Update progress display for batch operations."""
        try:
            loading_detail = self.query_one("#loading-detail", Static)
            loading_detail.update(f"[green]⚡[/] {status}")

            loading_stats = self.query_one("#loading-stats", Static)
            if total > 0:
                pct = int((current / total) * 100)
                loading_stats.update(
                    f"[dim]Progress:[/] {current}/{total} ({pct}%)  "
                    f"[dim]Found:[/] [green]{found}[/]"
                )
            else:
                loading_stats.update(f"[dim]Found:[/] [green]{found}[/]")
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
            elif event.worker.name == "_fetch_sectors_async":
                # Sector fetch completed - update sector list
                sectors = event.worker.result
                if sectors:
                    self._update_sectors_ui(sectors)
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
            elif event.worker.name == "_fetch_portfolio":
                # Portfolio fetch completed - display P&L view
                portfolio = event.worker.result
                if portfolio:
                    self._populate_portfolio_table(portfolio)
                else:
                    self.notify("Failed to load portfolio data", severity="error")
                    # Fall back to regular table
                    loading = self.query_one("#loading", Container)
                    loading.display = False
            else:
                # Stock fetch worker
                self.stocks = event.worker.result or []
                self._populate_table()

    def _get_view_mode(self, stocks: list) -> str:
        """Determine view mode based on asset types in stock list.

        Returns:
            'stock', 'etf', or 'mixed'
        """
        if not stocks:
            return "stock"

        etf_count = sum(1 for s in stocks if getattr(s, "asset_type", "stock") == "etf")
        stock_count = len(stocks) - etf_count

        if etf_count == 0:
            return "stock"
        elif stock_count == 0:
            return "etf"
        else:
            return "mixed"

    def _get_columns_for_mode(self, mode: str) -> tuple:
        """Get column headers for the given view mode."""
        if mode == "etf":
            return ETF_COLUMNS
        elif mode == "mixed":
            return MIXED_COLUMNS
        else:
            return STOCK_COLUMNS

    def _format_etf_row(self, stock, format_price_func) -> tuple:
        """Format a row for ETF display."""
        # Company name with ticker
        company_name = stock.name or stock.ticker
        if len(company_name) > 25:
            company_name = company_name[:22] + "..."
        company = f"{company_name} ({stock.ticker})"

        # Category (use sector field which stores category for ETFs)
        category = _truncate_sector(stock.sector) if stock.sector else "-"

        # Price
        stock_currency = stock.currency or "USD"
        price = format_price_func(
            stock.current_price,
            currency=stock_currency,
            display_currency=self._display_currency,
            decimals=0,
        ) if stock.current_price else "-"

        # Expense Ratio
        exp_ratio = "-"
        if stock.etf.expense_ratio is not None:
            exp_ratio = f"{stock.etf.expense_ratio:.2f}%"

        # AUM (format in billions/millions)
        aum = "-"
        if stock.etf.aum:
            if stock.etf.aum >= 1_000_000_000:
                aum = f"${stock.etf.aum / 1_000_000_000:.1f}B"
            elif stock.etf.aum >= 1_000_000:
                aum = f"${stock.etf.aum / 1_000_000:.0f}M"
            else:
                aum = f"${stock.etf.aum / 1_000:.0f}K"

        # YTD Return
        ytd = "-"
        if stock.etf.ytd_return is not None:
            ytd = f"{stock.etf.ytd_return:+.1f}%"

        # 1Y Return (from technical indicators)
        return_1y = "-"
        if stock.technical.return_1y is not None:
            return_1y = f"{stock.technical.return_1y:+.1f}%"

        # Dividend yield
        div_val = stock.dividends.dividend_yield
        div = f"{div_val:.1f}%" if div_val else "-"

        # Signal
        signal = stock.signal

        return (company, category, price, exp_ratio, aum, ytd, return_1y, div, signal)

    def _format_stock_row(self, stock, format_price_func) -> tuple:
        """Format a row for stock display."""
        # Company name with ticker
        company_name = stock.name or stock.ticker
        if len(company_name) > 25:
            company_name = company_name[:22] + "..."
        company = f"{company_name} ({stock.ticker})"

        # Sector
        sector = _truncate_sector(stock.sector) if stock.sector else "-"

        # Price
        stock_currency = stock.currency or "USD"
        price = format_price_func(
            stock.current_price,
            currency=stock_currency,
            display_currency=self._display_currency,
            decimals=0,
        ) if stock.current_price else "-"

        # P/E
        pe = f"{stock.valuation.pe_trailing:.1f}" if stock.valuation.pe_trailing and isinstance(stock.valuation.pe_trailing, (int, float)) else "-"

        # ROE
        roe = f"{stock.profitability.roe:.0f}%" if stock.profitability.roe else "-"

        # RSI
        rsi = f"{stock.technical.rsi_14:.0f}" if stock.technical.rsi_14 else "-"

        # Margin of Safety
        mos_val = stock.fair_value.margin_of_safety_pct
        mos = f"{mos_val:+.0f}%" if mos_val else "-"

        # Dividend yield
        div_val = stock.dividends.dividend_yield
        div = f"{div_val:.1f}%" if div_val else "-"

        # Signal
        signal = stock.signal

        return (company, sector, price, pe, roe, rsi, mos, div, signal)

    def _format_mixed_row(self, stock, format_price_func) -> tuple:
        """Format a row for mixed stock/ETF display."""
        # Company name with ticker
        company_name = stock.name or stock.ticker
        if len(company_name) > 25:
            company_name = company_name[:22] + "..."
        company = f"{company_name} ({stock.ticker})"

        # Type indicator
        asset_type = getattr(stock, "asset_type", "stock")
        type_str = "ETF" if asset_type == "etf" else "Stock"

        # Sector/Category
        sector = _truncate_sector(stock.sector) if stock.sector else "-"

        # Price
        stock_currency = stock.currency or "USD"
        price = format_price_func(
            stock.current_price,
            currency=stock_currency,
            display_currency=self._display_currency,
            decimals=0,
        ) if stock.current_price else "-"

        # Dividend yield
        div_val = stock.dividends.dividend_yield
        div = f"{div_val:.1f}%" if div_val else "-"

        # 1Y Return
        return_1y = "-"
        if stock.technical.return_1y is not None:
            return_1y = f"{stock.technical.return_1y:+.1f}%"

        # RSI
        rsi = f"{stock.technical.rsi_14:.0f}" if stock.technical.rsi_14 else "-"

        # Signal
        signal = stock.signal

        return (company, type_str, sector, price, div, return_1y, rsi, signal)

    def _populate_table(self) -> None:
        loading = self.query_one("#loading", Container)
        table = self.query_one("#results-table", DataTable)

        loading.display = False
        table.display = True

        # Determine view mode based on asset types
        view_mode = self._get_view_mode(self.stocks)
        columns = self._get_columns_for_mode(view_mode)

        # If we were in portfolio mode or columns changed, reconfigure
        if self._portfolio_mode or len(table.columns) != len(columns):
            table.clear(columns=True)
            table.add_columns(*columns)
            self._portfolio_mode = False
        else:
            table.clear()

        # Handle empty results with helpful feedback
        if not self.stocks:
            self._show_empty_results_feedback()
            return

        # Sort stocks according to current sort setting
        sort_key, default_reverse, sort_name = self.SORT_OPTIONS[self.current_sort]
        # XOR with sort_reverse to toggle direction
        reverse = default_reverse != self.sort_reverse
        sorted_stocks = sorted(self.stocks, key=sort_key, reverse=reverse)

        # Add rows based on view mode
        from tradfi.utils.display import format_price
        for stock in sorted_stocks:
            if view_mode == "etf":
                row = self._format_etf_row(stock, format_price)
            elif view_mode == "mixed":
                row = self._format_mixed_row(stock, format_price)
            else:
                row = self._format_stock_row(stock, format_price)

            table.add_row(*row, key=stock.ticker)

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
            if self.selected_sectors:
                count = len(self.selected_sectors)
                filter_parts.append(f"{count} sec")

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

    def _show_empty_results_feedback(self) -> None:
        """Show helpful feedback when screening returns no results."""
        # Build explanation of why no results
        issues = []
        suggestions = []

        # Check if preset is too restrictive
        if self.current_preset:
            preset_name = PRESET_INFO.get(self.current_preset, {}).get("name", self.current_preset)
            preset_criteria = PRESET_INFO.get(self.current_preset, {}).get("criteria", "")
            issues.append(f"Preset '{preset_name}' ({preset_criteria}) filtered all stocks")
            suggestions.append("Try 'None (Custom)' preset")

        # Check sector filter mismatch
        if self.selected_sectors and self.selected_universes:
            universes = ", ".join(sorted(self.selected_universes))
            sectors = ", ".join(sorted(list(self.selected_sectors)[:2]))
            if len(self.selected_sectors) > 2:
                sectors += f" +{len(self.selected_sectors) - 2} more"
            issues.append(f"Sectors '{sectors}' may not exist in '{universes}'")
            suggestions.append("Clear sector filter or select different universe")

        # Check category filter
        if self.selected_categories and self.selected_universes:
            cats = ", ".join(sorted(self.selected_categories))
            issues.append(f"Categories '{cats}' may have no matching stocks")
            suggestions.append("Clear category filter")

        # Default message
        if not issues:
            if self.selected_universes:
                issues.append("No stocks match current filter combination")
            else:
                issues.append("No cached data available")
            suggestions.append("Press 'c' to clear all filters")

        # Format status message
        issue_text = issues[0] if issues else "No results"
        suggestion_text = suggestions[0] if suggestions else "Try different filters"

        self._update_status(
            f"[yellow]No results:[/] {issue_text}. "
            f"[dim]Suggestion: {suggestion_text}[/]"
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
                "sector": self.action_focus_sector,
                "clear": self.action_clear_filters,
                "refresh": self.action_refresh,
                "save": self.action_save_list,
                "cache_manage": self.action_cache_manage,
                "clear_cache": self.action_clear_cache,
                "resync": self.action_resync_universes,
                "help": self.action_help,
                # Discovery presets
                "preset_fallen": self.action_preset_fallen_angels,
                "preset_hidden": self.action_preset_hidden_gems,
                "preset_turnaround": self.action_preset_turnaround,
                "preset_momentum": self.action_preset_momentum_value,
                "preset_dividend": self.action_preset_dividend_growers,
                # Visualizations
                "heatmap": self.action_show_heatmap,
                "scatter": self.action_show_scatter,
                "currency": self.action_toggle_currency,
                # Sort options
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
                "sort_sector": self.action_sort_sector,
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
            "Detail view: l=Long x=Short w=Watchlist d=Research m=Similar\n"
            "Visualizations: h=Heatmap p=Scatter | $=Currency",
            title="Help",
            timeout=10,
        )

    def action_toggle_currency(self) -> None:
        """Toggle display currency (USD -> EUR -> GBP -> JPY -> AUD -> ZAR -> XAU)."""
        from tradfi.core.currency import get_currency_symbol

        # Cycle to next currency
        try:
            current_idx = self._currency_cycle.index(self._display_currency)
            next_idx = (current_idx + 1) % len(self._currency_cycle)
        except ValueError:
            next_idx = 0
        self._display_currency = self._currency_cycle[next_idx]

        # Update the currency indicator
        try:
            indicator = self.query_one("#currency-indicator", Static)
            symbol = get_currency_symbol(self._display_currency)
            indicator.update(f"[yellow]{self._display_currency}[/]")
        except Exception:
            pass

        # Notify user
        self.notify(
            f"Display currency: {self._display_currency}",
            title="Currency Changed",
            timeout=2,
        )

        # Refresh the table to show prices in new currency
        if self.stocks:
            self._populate_table()

    # === Visualization Actions ===
    def action_show_heatmap(self) -> None:
        """Show sector heatmap visualization."""
        if not self.stocks:
            self.notify("No stocks to visualize. Run a screen first.", severity="warning")
            return

        def on_sector_selected(sector: str | None) -> None:
            if sector:
                # Filter stocks to selected sector
                self.stocks = [s for s in self.stocks if s.sector == sector]
                self._populate_table()
                self._update_status(f"Filtered to sector: {sector} ({len(self.stocks)} stocks)")

        self.push_screen(SectorHeatmapScreen(self.stocks.copy()), on_sector_selected)

    def action_show_scatter(self) -> None:
        """Show scatter plot visualization."""
        if not self.stocks:
            self.notify("No stocks to visualize. Run a screen first.", severity="warning")
            return

        self.push_screen(ScatterPlotScreen(self.stocks.copy()))

    # === Discovery Preset Actions ===
    def _run_discovery_preset(self, preset_name: str) -> None:
        """Run a discovery preset screen."""
        self.current_preset = preset_name
        self._update_filter_pills()
        desc = PRESET_DESCRIPTIONS.get(preset_name, preset_name)
        self.notify(f"Running: {desc}", title=f"Discovery: {preset_name}", timeout=3)
        self._run_screen()

    def action_preset_fallen_angels(self) -> None:
        """Screen for fallen angels - quality stocks down 30%+."""
        self._run_discovery_preset("fallen-angels")

    def action_preset_hidden_gems(self) -> None:
        """Screen for hidden gems - small/mid cap quality stocks."""
        self._run_discovery_preset("hidden-gems")

    def action_preset_turnaround(self) -> None:
        """Screen for turnaround candidates."""
        self._run_discovery_preset("turnaround")

    def action_preset_momentum_value(self) -> None:
        """Screen for momentum + value stocks."""
        self._run_discovery_preset("momentum-value")

    def action_preset_dividend_growers(self) -> None:
        """Screen for sustainable dividend payers."""
        self._run_discovery_preset("dividend-growers")

    def action_cache_manage(self) -> None:
        """Open the cache management screen."""
        self.push_screen(CacheManagementScreen(self.remote_provider))

    def action_clear_cache(self) -> None:
        """Clear all cached stock data on the server."""
        self.notify("Clearing cache...", title="Cache")
        self.run_worker(self._do_clear_cache_action(), exclusive=True, thread=True)

    def _do_clear_cache_action(self) -> None:
        """Worker to clear all cached stock data on the server."""
        count = self.remote_provider.clear_cache()
        self.call_from_thread(self.notify, f"Cleared {count} cached entries on server", title="Cache Cleared")

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

        self._update_sort_indicator()
        self._populate_table()

    def _update_sort_indicator(self) -> None:
        """Update the sort indicator in the bottom bar."""
        try:
            indicator = self.query_one("#sort-indicator", Static)
            _, default_reverse, sort_name = self.SORT_OPTIONS[self.current_sort]
            # XOR with sort_reverse to get actual direction
            is_descending = default_reverse != self.sort_reverse
            direction = "↓" if is_descending else "↑"
            indicator.update(f"[cyan]Sort: {sort_name} {direction}[/]")
        except Exception:
            pass

    def action_sort_ticker(self) -> None:
        self._sort_by("ticker")

    def action_sort_sector(self) -> None:
        self._sort_by("sector")

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

    def action_focus_sector(self) -> None:
        """Focus the sector or category selection list based on current universe."""
        if self._is_etf_only_selection():
            # ETF mode: focus categories
            category_select = self.query_one("#category-select", SelectionList)
            category_select.focus()
        else:
            # Stock mode: focus sectors
            sector_select = self.query_one("#sector-select", SelectionList)
            sector_select.focus()

    def action_clear_filters(self) -> None:
        """Clear all universe, category, and sector selections."""
        try:
            universe_select = self.query_one("#universe-select", SelectionList)
            universe_select.deselect_all()
            self.selected_universes = set()

            # Clear categories
            category_select = self.query_one("#category-select", SelectionList)
            category_select.deselect_all()
            self.selected_categories = set()

            # Clear sectors
            sector_select = self.query_one("#sector-select", SelectionList)
            sector_select.deselect_all()
            self.selected_sectors = set()

            # Clear preset
            self.current_preset = None
            preset_list = self.query_one("#preset-list", OptionList)
            preset_list.highlighted = 0  # Select "None (Custom)"

            # Reset visibility to default (show Sectors)
            self._update_filter_section_visibility()
            self._update_sectors_for_selection()

            # Update section titles and filter pills to reflect cleared state
            self._update_section_titles()
            self._update_filter_pills()

            self.notify("All filters cleared", timeout=2)
            self._run_screen()
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes for real-time filtering."""
        if event.input.id == "sector-search":
            self._display_filtered_sectors(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "search-input":
            ticker = event.value.strip().upper()
            if ticker:
                self._search_ticker(ticker)
                event.input.value = ""  # Clear the input
        elif event.input.id == "sector-search":
            # Just filter on submit as well (already handled by on_input_changed)
            pass

    def _search_ticker(self, ticker: str) -> None:
        """Search for a single ticker and display it."""
        loading = self.query_one("#loading", Container)
        table = self.query_one("#results-table", DataTable)
        loading.display = True
        table.display = False

        loading_text = self.query_one("#loading-text", Static)
        loading_text.update("[cyan]SEARCHING[/]")

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
