# ReWorth — Know its worth before you replace it

A Flask + SQLite web app that helps people decide whether an old or damaged product should be **Repaired, Reused, Donated, Recycled or Replaced** — with an explainable, rule-based score instead of a black box.
*Mini Project – I (Real-World Application Development).*

## Features
- 4-step assessment (guests can use it; logged-in users get saved history)
- Transparent engine: score, confidence, information quality, factor breakdown, next step; says **Diagnosis Required** when information is too thin; never invents prices
- Accounts: register/login, profile, change password, CSV export, delete account, password-reset links
- Admin area: statistics, filters, CSV export, user/role management, reset-link generation
- Security: CSRF, hashed passwords, throttling, secure cookies/headers, CSV-injection protection
- 31 automated tests + GitHub Actions CI + Render Blueprint

## Quick start
```bash
python -m venv venv && venv\Scripts\activate        # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python app.py                                         # http://127.0.0.1:5000
pytest -v
```
Locally, an admin `admin@reworth.local` / `ReWorth@123` is created automatically (log in at `/admin/login`; change it with `REWORTH_ADMIN_PASSWORD`).
**Forgot password locally:** no email server is needed — the reset link is printed in the VS Code terminal where `python app.py` is running; open it in the browser. Or log in as admin → Users → *Reset link*.
To bring back the old classroom shortcuts (direct reset + "Use demo admin" button), start with `REWORTH_DEMO_MODE=1` (PowerShell: `$env:REWORTH_DEMO_MODE=1; python app.py`).

## Deploy
See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** — GitHub push, then Render → New → Blueprint (uses `render.yaml`).

| Environment variable | Purpose |
|---|---|
| `REWORTH_ENV=production` | Secure defaults (set by `render.yaml`) |
| `REWORTH_SECRET_KEY` | Required in production (auto-generated on Render) |
| `REWORTH_ADMIN_EMAIL`, `REWORTH_ADMIN_PASSWORD` | Admin account in production |
| `REWORTH_DB_PATH` | SQLite location (use a disk path for persistence) |
| `REWORTH_SMTP_HOST/PORT/USER/PASSWORD/FROM` | Optional reset emails |
| `REWORTH_DEMO_MODE=1` | Opt-in: direct email-only reset + demo-admin button (never on a public site) |

## Project layout
```
app.py                  Flask app, engine, API, auth, admin
templates/  static/     UI
tests/                  pytest suite + load_test.py
docs/                   SRS, SDLC plan, UML, architecture, test report,
                        security & performance, deployment, manual, report, viva
render.yaml  Procfile  .github/workflows/ci.yml
```
Start with **[docs/TECHNICAL_REPORT.md](docs/TECHNICAL_REPORT.md)** for the full deliverables index.
