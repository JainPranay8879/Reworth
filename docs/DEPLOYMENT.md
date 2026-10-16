# Deployment Guide — GitHub + Render

## A. Run locally
```bash
python -m venv venv && venv\Scripts\activate      # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt -r requirements-dev.txt
python app.py                                      # http://127.0.0.1:5000
pytest -v                                          # run the 31 tests
```
A local admin `admin@reworth.local` / `ReWorth@123` is created automatically. *Forgot password* prints the reset link in the terminal (no email server needed). Set `REWORTH_DEMO_MODE=1` to enable the old direct reset and the "Use demo admin" button for classroom demos.

## B. Push to GitHub
```bash
git init
git add .
git commit -m "ReWorth: initial release"
git branch -M main
git remote add origin https://github.com/<your-username>/reworth.git   # create an empty repo first
git push -u origin main
```
GitHub Actions runs the tests automatically (Actions tab). Do **not** commit `.env` or `*.db` (already in `.gitignore`).

## C. Deploy on Render (Blueprint — easiest)
1. Render dashboard → **New → Blueprint** → connect your GitHub repo.
2. Render reads `render.yaml`. When asked, enter **`REWORTH_ADMIN_EMAIL`** and a strong **`REWORTH_ADMIN_PASSWORD`** (8+ chars). `REWORTH_SECRET_KEY` is generated automatically.
3. Click **Apply**. After the build, open the URL Render gives you (`https://reworth-xxxx.onrender.com`).
4. Check `/health` returns `{"status":"ok"}`, then log in at `/admin/login`.
Every `git push` to `main` redeploys automatically.

### Manual alternative (New → Web Service)
| Field | Value |
|---|---|
| Runtime | Python 3 |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn app:app --preload --workers 2 --threads 4 --timeout 60` |
| Health check path | `/health` |
| Env vars | `REWORTH_ENV=production`, `REWORTH_SECRET_KEY=<long random>`, `REWORTH_ADMIN_EMAIL`, `REWORTH_ADMIN_PASSWORD` |

## D. Things to know
- **Data persistence:** on Render's free plan the disk is wiped on each deploy/restart, so accounts and history reset. For a demo that is fine (the admin is re-created from env vars). For persistence use a paid instance + disk and set `REWORTH_DB_PATH=/var/data/reworth.db`.
- **Cold start:** free instances sleep after ~15 min idle; the first request is slow. Open the site before your demo.
- **Password reset in production:** either configure SMTP (`REWORTH_SMTP_HOST`, `_PORT`, `_USER`, `_PASSWORD`, `_FROM`) or use **Admin → Users → Reset link** and give the link to the user.
- **Without SMTP**, reset links are written to Render → Logs; or use the admin Reset link button.
- **Viva demo of the old direct reset?** Run locally with `REWORTH_DEMO_MODE=1` — never on a public site.
- **Troubleshooting:** build fails → check Python version (`.python-version`); "REWORTH_SECRET_KEY must be set" → add the env var; cannot log in as admin → confirm env vars and redeploy (admin is synced on start-up).
