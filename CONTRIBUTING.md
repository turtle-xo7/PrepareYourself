# Contributing to PrepareYourself

Thank you for your interest in contributing! This document explains how to get your changes into the project smoothly.

---

## Development Setup

1. Fork the repository and clone your fork:
   ```bash
   git clone https://github.com/<your-username>/PrepareYourself.git
   cd PrepareYourself
   ```

2. Run the one-time setup:
   ```bat
   setup.bat          # Windows
   ```
   Or manually:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python manage.py migrate
   ```

3. Create a feature branch:
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

---

## Coding Standards

- Follow [PEP 8](https://pep8.org/) for Python code.
- Keep views, models, and templates focused — one responsibility per function.
- Avoid committing `print()` debug statements.
- Do not commit `db.sqlite3`, `media/`, or `.env` files (they are gitignored).
- All user-facing strings that could appear in Bangla should go through the existing bilingual notification/template system where applicable.

---

## Writing Tests

We have two layers of tests:

### Unit Tests (`core/test.py`)
For model logic, view responses, and form validation:
```bash
python manage.py test core
```

### Selenium E2E Tests (`core/test_selenium/`)
For user flows through the browser. Add new flows under the appropriate module or create a new file following the existing pattern:
```bash
python manage.py test core.test_selenium
```

**All pull requests must include tests for new features or bug fixes.**

---

## Pull Request Process

1. Ensure `python manage.py test core` passes.
2. Write a clear PR description using the [PR template](.github/pull_request_template.md).
3. Link any related issues with `Closes #<issue-number>`.
4. Request a review from at least one team member.
5. PRs are merged by the team lead after review approval.

---

## Reporting Bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md). Include:
- Steps to reproduce
- Expected vs. actual behavior
- Django version, Python version, browser (for UI bugs)
- Relevant error messages or tracebacks

---

## Requesting Features

Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md).

---

## Commit Message Style

```
type(scope): short description

Longer explanation if needed (wrap at 72 chars).
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

Examples:
```
feat(exam): add per-part marks breakdown on CQ result page
fix(auth): redirect to next URL after login instead of hardcoded home
test(selenium): add contest leaderboard E2E test
```

---

## Questions?

Open a [GitHub Discussion](https://github.com/turtle-xo7/PrepareYourself/discussions) or mention a team member in an issue.
