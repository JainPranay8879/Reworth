# ReWorth Admin Dashboard Guide

## What it provides

- Role-based administrator access
- Admin login at `/admin/login`
- Dashboard KPIs: users, assessments, average score and low-confidence assessments
- Recommendation distribution for Repair, Reuse, Donate, Recycle, Replace and Diagnosis Required
- Category distribution
- Search and filters for saved assessments
- Individual assessment detail pages with decision factors and explanation
- User management and admin-role assignment
- Protection against removing your own admin role
- CSV export of all or filtered assessments

## First-time setup

1. Open a terminal in the inner `ReWorth` folder (the folder containing `app.py`).
2. Install dependencies: `python -m pip install -r requirements.txt`
3. Create an admin: `python app.py create-admin`
4. Enter the requested name, email and password.
5. Start the website: `python app.py`
6. Open `http://127.0.0.1:5000/admin/login`.

If an account with the entered email already exists, the setup command promotes it to admin and resets its password to the new password.

## Password-reset links
**Admin → Users → Reset link** creates a single-use link (valid 30 minutes) for that user and shows it at the top of the page. Send it to the user securely.

## Production notes
CSRF protection, HTTPS (via Render), a required secret key, gunicorn and login throttling are built in. Still recommended for a real service: audit logging, MFA, a Content-Security-Policy and a managed database.


## Built-in demo administrator (local/demo mode only)

When `REWORTH_ENV` is not `production`, the app creates an administrator automatically on start-up (the demo button on the login page appears only with `REWORTH_DEMO_MODE=1`).
**In production no default admin exists**: set `REWORTH_ADMIN_EMAIL` and `REWORTH_ADMIN_PASSWORD` (8+ characters) and the admin is created/synchronised on start-up.

**Email:** `admin@reworth.local`  
**Password:** `ReWorth@123`

Open **Admin** in the website navigation or visit `/admin/login`. In demo mode the login page includes a **Use demo admin** button (hidden in production).

For any public deployment, override these values with the environment variables `REWORTH_ADMIN_EMAIL` and `REWORTH_ADMIN_PASSWORD`, and do not publish demo credentials.
