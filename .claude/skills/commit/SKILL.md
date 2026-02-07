Review all changes and create a well-crafted git commit. Follow these steps exactly:

1. Run `git status` and `git diff` to understand all changes (staged and unstaged).

2. Run `ruff check .` and `ruff format --check .`. If there are lint or format issues, fix them first before committing.

3. Run `pytest` to make sure tests pass. If any test fails, stop and fix it before committing. Do NOT commit broken code.

4. Analyze the changes and draft a commit message:
   - First line: concise summary under 72 chars (imperative mood: "Add", "Fix", "Update")
   - Blank line
   - Body: explain the WHY, not the what. What problem does this solve?
   - If multiple logical changes are mixed, suggest splitting into separate commits.

5. Stage only the relevant files (no `git add .` — be explicit about what's included).

6. Do NOT commit files that contain secrets (.env, API keys, credentials).

7. Create the commit and show the result.

8. Ask if the user wants to push.
