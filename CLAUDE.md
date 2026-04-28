# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PrepareYourself** is a Django-based e-learning platform for SSC/HSC students with question banks, progress tracking, live contests, AI-powered study tools, and teacher dashboards.

## Commands

```bash
# Run development server
python manage.py runserver

# Run all tests
python manage.py test

# Run specific test file
python manage.py test core.tests_selenium.SeleniumTests

# Run Selenium tests only
python manage.py test core.tests_selenium

# Run unit tests only
python manage.py test core.tests

# Make migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic
```

## Architecture

### Core Apps
- **`core/`** - Main application with all business logic, models, views, and templates
- **`users/`** - Legacy auth module (minimal, most auth handled in core)
- **`prepare_yourself/`** - Django project configuration (settings, urls, wsgi)

### Key Models (`core/models.py`)
- `Board`, `Subject`, `Class` - Educational taxonomy
- `Question` - Question bank with MCQ/written types, difficulty levels
- `UserProfile` - Extends User with role (STUDENT/ADMIN), plan (FREE/BASIC/PREMIUM), superadmin flag
- `UserProgress`, `TeacherFeedback` - Student tracking and teacher communication
- `StudyNote`, `NoteBookmark`, `NoteReadProgress`, `NoteComment` - Study materials system
- `Contest`, `ContestQuestion`, `ContestSubmission`, `ContestAnswer` - Live contest system
- `Syllabus` - Board/class/subject curriculum
- `PracticalVideo` - YouTube video integration

### Access Control
Three custom decorators in `core/views.py`:
- `@admin_required` - Role must be 'ADMIN' (teachers)
- `@superadmin_required` - Must have `is_superadmin=True`
- `@premium_required` - Must have BASIC/PREMIUM plan or be admin

### AI Integration (`core/views.py`)
Direct HTTP calls to Anthropic API for:
- Note generation (`generate_note_ai`)
- MCQ generation from notes (`generate_mcq`)
- Note summarization (`summarize_note`)
- Contextual Q&A (`ask_ai`)

API key placeholder: `'ENTER_API_KEY_HERE'` in lines 995, 1051, 1096, 1138

### URL Routing
- Root: `prepare_yourself/urls.py` → includes `core.urls`
- All views in `core/views.py` (1400+ lines)
- Templates in `templates/core/`, `templates/manage/`, `templates/teacher/`

### Testing
- **Unit tests:** `core/tests.py` (minimal, extendable)
- **Selenium tests:** `core/tests_selenium.py` - Full browser tests for auth, navigation, question bank, superadmin features
- Test helpers: `create_student()`, `create_teacher()`, `create_superadmin()`, `login()`
- Test decorators handle logging suppression and test-specific settings

### Settings Highlights (`prepare_yourself/settings.py`)
- SQLite3 database
- Email via Gmail SMTP (configured credentials)
- Jazzmin admin theme
- Test mode disables DEBUG, redirects logging
- `--fast` flag uses in-memory database

### Frontend
- Django templates with Bootstrap
- Custom context processor: `core.context_processors.user_role`
- Static files in `static/`, media in `media/`
- 45+ HTML templates across core, manage, teacher, users sections
