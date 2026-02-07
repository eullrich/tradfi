Find and report technical debt in the codebase. Specifically:

1. **Duplicated code**: Search for repeated patterns across files (3+ lines that appear in multiple places). Focus on `src/tradfi/commands/` and `src/tradfi/core/`.

2. **Missing error handling**: Find places where yfinance data is accessed without None checks. Cross-reference with patterns in `core/screener.py` which does this correctly.

3. **TODO/FIXME/HACK comments**: Find all of these and rank by severity.

4. **Type annotation gaps**: Find functions missing return type annotations or parameter types.

5. **Dead code**: Find imports that aren't used, functions that aren't called, and unreachable code paths.

Output a prioritized report as a Rich-formatted table with columns: File, Line, Issue, Severity (high/medium/low), Suggested Fix.

After the report, offer to fix the top 3 highest-severity issues automatically.
