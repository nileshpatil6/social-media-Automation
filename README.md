# Social Media Automation

AI-powered platform for generating, quality-checking, scheduling and publishing advertisement content across Instagram, Facebook, X (Twitter), LinkedIn and YouTube.

The system turns a short topic description into a finished, on-brand advertisement image, evaluates it automatically with a vision model, and publishes it to one or more social channels, either immediately or on a schedule.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

---

## Overview

The content pipeline runs in five stages:

1. **Prompt generation**: Google Gemini converts a topic and description into an optimized image prompt.
2. **Image generation**: Ideogram renders a professional advertisement image.
3. **Quality analysis**: Gemini Vision scores the result on semantic match, visual quality, brand suitability and technical quality.
4. **Decision**: the image is approved, edited or regenerated based on its score.
5. **Publishing**: approved content is posted to the selected platforms, now or at a scheduled time.

## Key Features

- **AI content generation** with Gemini (prompting) and Ideogram (image rendering).
- **Automated quality control** using a scored review and a threshold-based decision engine.
- **Multi-platform publishing** to Instagram, Facebook, X, LinkedIn and YouTube from a single request.
- **Scheduling** backed by the database, with a background runner, automatic retries and failure tracking.
- **Automation plans** that generate a full content calendar and activate it in one step.
- **Batch processing** through Excel upload for large volumes of topics.
- **Multi-user support** with JWT authentication and per-user data isolation.
- **Web dashboard** for generation, scheduling and plan management.

### Quality Decision Logic

| Overall score | Decision       | Action                                  |
|---------------|----------------|-----------------------------------------|
| 7.5 and above | `APPROVE`      | Ready to publish                        |
| 6.0 to 7.4    | `EDIT`         | Apply targeted improvements             |
| Below 6.0     | `REGENERATE`   | Create a new image with a refined prompt |

## Architecture

```
            ┌──────────────┐
 Topic ───► │ Gemini       │  prompt generation
            └──────┬───────┘
                   ▼
            ┌──────────────┐
            │ Ideogram     │  image generation
            └──────┬───────┘
                   ▼
            ┌──────────────┐
            │ Gemini Vision│  quality scoring
            └──────┬───────┘
                   ▼
        APPROVE / EDIT / REGENERATE
                   ▼
            ┌──────────────┐     ┌───────────────────────────────┐
            │ Scheduler    │ ──► │ Platform agents               │
            └──────────────┘     │ Instagram · Facebook · X      │
                                 │ LinkedIn · YouTube            │
                                 └───────────────────────────────┘
```

## Tech Stack

| Layer          | Technology                                   |
|----------------|----------------------------------------------|
| Backend        | Python, FastAPI, Uvicorn                      |
| Database       | SQLAlchemy (SQLite by default, PostgreSQL supported) |
| AI services    | Google Gemini 2.5 Flash, Ideogram             |
| Authentication | JWT (python-jose), bcrypt                     |
| Data handling  | pandas, openpyxl, Pillow                      |
| Frontend       | Jinja2 templates, CSS                         |
| Integrations   | Meta Graph API, X API, LinkedIn API, YouTube Data API |

## Getting Started

### Prerequisites

- Python 3.10 or newer
- API credentials for Gemini, Ideogram and each social platform you plan to use
- Optional: PostgreSQL for production deployments

### Installation

```bash
git clone https://github.com/nileshpatil6/social-media-Automation.git
cd social-media-Automation

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file in the project root (see [Configuration](#configuration)), then start the server:

```bash
python app.py
```

The application is available at **http://localhost:8000**.

## Configuration

All configuration is read from environment variables, typically via a `.env` file.

### Core

| Variable                           | Required | Description                                          |
|------------------------------------|----------|------------------------------------------------------|
| `GEMINI_API_KEY`                   | Yes      | Google AI Studio API key                             |
| `IDEOGRAM_API_KEY`                 | Yes      | Ideogram API key                                     |
| `JWT_SECRET_KEY`                   | Yes      | Secret used to sign authentication tokens            |
| `JWT_ALGORITHM`                    | No       | Token signing algorithm                              |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`  | No       | Token lifetime in minutes                            |
| `DATABASE_URL`                     | No       | Database connection string (default `sqlite:///./adgen.db`) |
| `PORT`                             | No       | Server port (default `8000`)                         |
| `PUBLIC_BASE_URL`                  | No       | Public URL used to serve generated images            |
| `STORAGE_PATH`                     | No       | Local directory for generated images                 |
| `IMGBB_API_KEY` / `IMGUR_CLIENT_ID`| No       | Fallback image hosts for platforms that need a public URL |
| `SCHEDULER_POLL_INTERVAL`          | No       | Seconds between scheduler checks                     |
| `SCHEDULER_STARTUP_DELAY`          | No       | Delay before the scheduler starts                    |

### Platforms

| Platform  | Variables |
|-----------|-----------|
| Instagram | `FACEBOOK_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ACCOUNT_ID` |
| Facebook  | `FACEBOOK_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID` |
| X         | `TWITTER_API_KEY`, `TWITTER_API_SECRET_KEY`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET` |
| LinkedIn  | `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_URN` (e.g. `urn:li:person:XXXX`), optional `LINKEDIN_ORGANIZATION_ID` |
| YouTube   | `YOUTUBE_CLIENT_SECRETS_FILE`, `YOUTUBE_CREDENTIALS_FILE` (OAuth) |

Only configure the platforms you intend to use. Setup guides for individual platforms are in [`docs/`](docs/).

> **Security note:** never commit `.env`, OAuth client secrets or credential files. Keep them out of version control.

## Usage

### Web dashboard

| Page      | Path      | Purpose                                      |
|-----------|-----------|----------------------------------------------|
| Dashboard | `/`       | Generation, scheduling and automation plans  |
| Quick ad  | `/simple` | Generate a single advertisement              |
| Sign in   | `/login`  | Account login                                |
| Sign up   | `/signup` | Account registration                         |

### Batch upload via Excel

Download the template from `GET /download-sample-excel`, fill it in, and upload it on the dashboard.

| Column                | Required | Description              |
|-----------------------|----------|--------------------------|
| `topic_title`         | Yes      | Advertisement topic      |
| `textual_description` | Yes      | Detailed description     |
| `date`                | No       | Posting date and time    |
| `target_accounts`     | No       | Target audience          |
| `image_constraints`   | No       | Visual requirements      |

**Example**

| date             | topic_title        | textual_description                                   | target_accounts   | image_constraints               |
|------------------|--------------------|-------------------------------------------------------|-------------------|---------------------------------|
| 2026-01-15 10:00 | Summer Sale        | Promote 50% off summer collection with bright visuals | @fashion_lovers   | Bright colors, show products    |
| 2026-01-16 14:00 | New Product Launch | Launch our latest smartwatch with modern imagery      | @tech_enthusiasts | Clean background, product focus |

## API Reference

All endpoints except registration and login require a bearer token.

### Authentication

| Method | Endpoint         | Description          |
|--------|------------------|----------------------|
| POST   | `/auth/register` | Register a new user  |
| POST   | `/auth/login`    | Obtain an access token |
| GET    | `/auth/me`       | Current user profile |

### Content generation

| Method | Endpoint                 | Description                          |
|--------|--------------------------|--------------------------------------|
| POST   | `/generate-ad`           | Generate a single advertisement      |
| POST   | `/upload-excel`          | Batch-create topics from Excel       |
| GET    | `/download-sample-excel` | Download the Excel template          |
| GET    | `/topics`                | List the current user's topics       |

### Publishing

| Method | Endpoint                     | Description                                  |
|--------|------------------------------|----------------------------------------------|
| POST   | `/post-to-instagram`         | Publish to Instagram                         |
| POST   | `/post-to-facebook`          | Publish to Facebook                          |
| POST   | `/post-to-twitter`           | Publish to X                                 |
| POST   | `/post-to-linkedin`          | Publish to LinkedIn                          |
| POST   | `/post-to-youtube`           | Upload to YouTube                            |
| POST   | `/post-direct-{platform}`    | Publish from a direct media URL (`facebook`, `twitter`, `linkedin`, `youtube`) |
| POST   | `/post-to-multiple-channels` | Publish to several platforms in one request  |

### Scheduling and automation

| Method | Endpoint                                   | Description                          |
|--------|--------------------------------------------|--------------------------------------|
| POST   | `/generate-and-schedule`                   | Generate content and schedule it     |
| POST   | `/schedule-automation`                     | Schedule a batch of posts            |
| POST   | `/auto-generate-and-post`                  | Generate and publish immediately     |
| GET    | `/scheduled-posts`                         | List scheduled posts                 |
| DELETE | `/scheduled-posts/{post_id}`               | Cancel a scheduled post              |
| POST   | `/scheduled-posts/{post_id}/retry`         | Retry a failed post                  |
| POST   | `/automation-plans/generate`               | Generate an automation plan          |
| GET    | `/automation-plans`                        | List automation plans                |
| GET    | `/automation-plans/{plan_id}`              | Get plan details                     |
| PUT    | `/automation-plans/{plan_id}`              | Update a plan                        |
| PUT    | `/automation-plans/{plan_id}/items/{item_id}` | Update a plan item                |
| DELETE | `/automation-plans/{plan_id}`              | Delete a plan                        |
| POST   | `/automation-plans/{plan_id}/activate`     | Activate a plan and schedule its posts |
| GET    | `/automation-timeline`                     | Timeline view of upcoming posts      |

Interactive API documentation is available at **http://localhost:8000/docs** while the server is running.

## Project Structure

```
social-media-Automation/
├── app.py                 # FastAPI application and routes
├── agents/                # Platform publishing agents (Instagram, Facebook, X, LinkedIn, YouTube)
├── auth/                  # JWT authentication
├── models/                # SQLAlchemy models and database setup
├── services/              # Generation, quality analysis, scheduling, Excel and upload services
├── templates/             # Jinja2 HTML templates
├── static/                # Stylesheets and static assets
├── scripts/               # Setup and token helper scripts
├── docs/                  # Platform setup guides and fix notes
├── tests/                 # Test suite
└── requirements.txt
```

## Testing

```bash
pytest
```

Some tests call live platform APIs and require valid credentials in `.env`.

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| Missing API keys | Confirm all required variables are set in `.env` and the keys are valid. |
| Image generation fails | Check the Ideogram API key and remaining credits. |
| Quality analysis errors | Confirm Gemini API access and that the generated image file exists. |
| Instagram posting fails | Verify token permissions and the Instagram Business Account link. See [`docs/INSTAGRAM_SETUP_GUIDE.md`](docs/INSTAGRAM_SETUP_GUIDE.md). |
| Facebook error `(#200)` | A Page Access Token with `pages_manage_posts` is required. See [`docs/FACEBOOK_PERMISSIONS_FIX.md`](docs/FACEBOOK_PERMISSIONS_FIX.md). |
| Scheduled post times are off | See [`docs/TIMEZONE_FIX_SUMMARY.md`](docs/TIMEZONE_FIX_SUMMARY.md). |

Helper scripts in [`scripts/`](scripts/) can retrieve page tokens and validate platform credentials.

## Roadmap

- Video advertisement generation
- TikTok publishing
- A/B testing with multiple creative variants
- Engagement analytics integration
- Brand-specific model tuning
