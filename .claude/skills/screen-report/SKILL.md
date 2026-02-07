Generate a comprehensive stock screening report. This skill analyzes the TradFi codebase to run screens and produce actionable output.

**Usage**: `/screen-report [preset] [universe]`
- Example: `/screen-report graham sp500`
- Example: `/screen-report fallen-angels nasdaq100`
- Example: `/screen-report` (defaults: all presets, sweetspot universe)

**Steps**:

1. Parse the arguments. Default preset = run ALL value presets (graham, buffett, deep-value, oversold-value, fallen-angels). Default universe = sweetspot.

2. For each preset, examine `core/screener.py` to explain what criteria are being applied in plain English.

3. Show the CLI command the user would run:
   ```
   tradfi screen --preset graham --universe sp500 --limit 30
   ```

4. If the API server is running (check `curl -s http://localhost:8000/api/v1/refresh/health`), execute the screen via the API and display results.

5. Produce a summary report:
   - How many stocks passed each preset
   - Overlap: stocks that appear in multiple presets (highest conviction)
   - Sector distribution of passing stocks
   - Top 5 stocks by margin of safety

6. Suggest which results to save as a list:
   ```
   tradfi list create screen-2026-02-07 TICKER1,TICKER2,...
   ```
