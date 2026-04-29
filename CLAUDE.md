# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**PrepareYourself** — a Django 5.2 web app for SSC/HSC exam prep (Bangladesh). Primary user-facing language is **Bangla (Bengali)**: flash-message strings, AI prompts, and UI copy are in Bangla — preserve this when editing. Time zone is `Asia/Dhaka`.

## Active vs. dead project package

There are two Django project packages in the repo. Only one is wired up:

- **`prepare_yourself/`** — the active project. `manage.py` sets `DJANGO_SETTINGS_MODULE=prepare_yourself.settings`; this is the package that owns `settings.py`, `urls.py`, `wsgi.py`. It installs the `core` app and uses the Jazzmin admin theme.
- **`PrepareYourself/`** — a vestigial alternate project package referencing the orphan `users/` app. It is **not** loaded by `manage.py`. Don't edit it expecting changes to take effect; don't add `users` to the active settings without checking that nothing else depends on the dead config.

Likewise the **`users/`** app (with its own `Profile`/`register`/`user_login` views) is unused at runtime. The real user-profile model is `core.UserProfile`.

## Common commands

```bash
# Setup
pip install -r requirements.txt
# requirements.txt is missing some runtime deps that the code imports — install them too:
pip install openpyxl selenium webdriver-manager

# Dev
python manage.py runserver
python manage.py makemigrations
python manage.py migrate
python manage.py shell

# Tests — see "Testing" section below
python manage.py test core.tests_selenium
python manage.py test core.tests_selenium.AuthSeleniumTests.test_successful_login

# Static
python manage.py collectstatic
```

`python manage.py createsuperuser` creates a Django `auth.User` but **does not** create the `core.UserProfile` row that the app's role/plan logic depends on — most views will redirect or 500 for such a user. Either create a `UserProfile` in the shell, or sign up via `/signup/` with admin code `PY2026ADMIN` (this grants role=ADMIN + is_superadmin=True).

## Architecture

### Single-app monolith
Almost all backend logic lives in **`core/`** (`models.py`, `views.py`, `urls.py`, `admin.py`, `context_processors.py`). `core/views.py` is a ~1500-line module of function-based views grouped by section comments — no DRF, no class-based views, no forms.py. Adding a new feature usually means: model in `models.py` → migration → view function in `views.py` → URL in `core/urls.py` → template under `templates/<section>/`.

### Three-tier authorization (built on `core.UserProfile`)
The auth model is `django.contrib.auth.User` + a one-to-one `core.UserProfile` with:
- `role`: `STUDENT` or `ADMIN` (ADMIN means "Teacher/Tutor/Institution", **not** Django staff/superuser)
- `plan`: `FREE` / `BASIC` / `PREMIUM` (`is_premium` = BASIC or PREMIUM)
- `is_superadmin`: bool — site-wide admin, separate from `User.is_superuser`

Authorization is enforced by three decorators defined at the top of `core/views.py`:
- `@admin_required` — `profile.role == 'ADMIN'`
- `@superadmin_required` — `profile.is_superadmin`
- `@premium_required` — `is_premium`, **bypassed** for ADMIN or superadmin

When adding views, pick the decorator deliberately — premium gating doubles as a paywall, and admin gating doubles as the teacher/tutor surface. The `core.context_processors.user_role` processor exposes `is_admin`, `is_superadmin`, `unread_count` to every template; navbar/footer rely on these.

### Login & signup quirks
- `/login/` accepts either username or email (email is resolved to username before `authenticate`).
- `/signup/` reads a hidden `admin_code` field — value `PY2026ADMIN` promotes the new account to ADMIN + superadmin. This is the only way to bootstrap a superadmin from the UI.
- Password reset uses Django's built-in `auth_views` with custom templates under `templates/core/password_reset*.html` and SMTP via Gmail (host/user/password are hardcoded in `settings.py`).

### URL surface (read `core/urls.py` for the full map)
Major sections — each maps to a comment block in `views.py`:
- `/`, `/question-bank/` (free users see only first 10 questions), `/dashboard/`, `/progress/`, `/track-progress/` (AJAX POST)
- `/practical-lab/`, `/practical-videos/` (premium gate)
- `/study-notes/...` — list, detail, add/edit/delete, bookmark, read-progress (AJAX), comments (with admin approval), AI generate/MCQ/summarize/ask
- `/contests/...` — list, create (admin), join, submit, leaderboard
- `/syllabus/...`
- `/manage/...` — admin CRUD for questions, boards, subjects, classes (templates under `templates/manage/`)
- `/teacher/...` — teacher dashboard, per-student detail, feedback (templates under `templates/teacher/`)
- `/superadmin/...` — user management + `/superadmin/export/` which streams a multi-sheet `.xlsx` via `openpyxl`

### Anthropic API integration (study notes AI features)
Four views call the Claude API directly with `urllib.request` (no SDK): `generate_note_ai`, `generate_mcq`, `summarize_note`, `ask_ai`. All four have `'x-api-key': 'ENTER_API_KEY_HERE'` hardcoded as a placeholder — these endpoints will 500 until a real key is pasted in. They target model `claude-sonnet-4-20250514`, which is **out of date**: when working in this code, prefer migrating to the latest Sonnet (`claude-sonnet-4-6` / `claude-sonnet-4-7`) and reading the key from an env var rather than perpetuating the literal. Prompts are written in Bangla and ask for Bangla responses.

### Templates layout
- `templates/base.html` — root layout, pulled in by everything
- `templates/includes/{navbar,footer}.html` — partials
- `templates/core/` — student-facing + shared (login, dashboard, study notes, contests, syllabus, pricing, password reset)
- `templates/manage/` — admin CRUD pages
- `templates/teacher/` — teacher dashboard + student detail

### Media & file uploads
`StudyNote.pdf_file` uploads to `media/notes/pdfs/` (`MEDIA_ROOT = BASE_DIR/media`). `core/urls.py` appends `static(MEDIA_URL, document_root=MEDIA_ROOT)` so uploads serve in dev. `X_FRAME_OPTIONS = 'SAMEORIGIN'` is set so PDFs can be `<iframe>`'d on the detail page.

### Database
SQLite (`db.sqlite3`) — committed to the repo and treated as the canonical dev fixture. Schema lives in `core/migrations/0001..0014`. Running `python manage.py migrate` against the committed DB is the expected setup path; there are no fixtures or seed scripts.

## Testing

Two test files in `core/`:

- **`core/tests_selenium.py`** — the canonical suite. `LiveServerTestCase`-based Selenium tests using `webdriver-manager` to fetch ChromeDriver. Run with `python manage.py test core.tests_selenium`. Covers auth, navbar, question bank, study notes, contests, profile, syllabus, superadmin.
- **`core/test.py`** — older mix of `TestCase` unit tests and Selenium tests that bind to `http://127.0.0.1:8000` directly. The Selenium half **requires a dev server already running on :8000** and won't work in CI as-is. The filename is also non-standard (Django test discovery still matches `test*.py`, so `manage.py test core` will run both files). Prefer adding new tests to `tests_selenium.py`.

`settings.py` has a `if 'test' in sys.argv:` branch that disables `STATICFILES_DIRS` and ensures `staticfiles/` and `media/` exist, so tests work without a populated `static/` dir.

## Things to know / gotchas

- `DEBUG=True`, `SECRET_KEY` hardcoded, Gmail SMTP password committed to `settings.py` — this is dev config; treat as such.
- The `core/admin.py` Jazzmin/admin registration imports the same models multiple times at the top — harmless but don't be surprised by duplication.
- Several views do `from .models import X` inside the function body rather than at module top — match the existing style when editing those views to avoid circular-import worries.
- `Question.year` is a free-form integer; the `YEARS` constant in `views.py` is just `[CURRENT_YEAR .. CURRENT_YEAR-5]` for dropdowns — it isn't enforced at the model level.
