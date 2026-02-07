Run the full test and lint suite, then report results. Follow the project's existing test patterns.

1. Run `ruff check .` from the project root. Report any lint errors.
2. Run `ruff format --check .` to verify formatting. Report any unformatted files.
3. Run `pytest -v` to execute the full test suite. Report pass/fail counts.

If there are failures:
- Analyze each failure and determine the root cause.
- Fix lint/format issues automatically (run `ruff check --fix .` and `ruff format .`).
- For test failures, diagnose whether it's a code bug or a test bug and fix accordingly.
- Re-run the full suite after fixes to confirm green.

If all pass:
- Report a summary: X tests passed, 0 lint errors, all files formatted.

**Test patterns** (follow these when writing new tests):
- Use `create_test_stock()` factory from existing test files for test data.
- Organize tests in classes: `TestFeatureName`.
- Always test: happy path, edge case (None values), and invalid data.
- See `tests/test_screener.py` as the canonical example.
