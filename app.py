from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from pathlib import Path
from datetime import datetime
from functools import wraps
import csv
import io
import sys
import getpass
import secrets
from datetime import timedelta
import smtplib
import time
from email.message import EmailMessage
from werkzeug.middleware.proxy_fix import ProxyFix

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("REWORTH_DB_PATH", BASE_DIR / "reworth.db"))

# --- Environment -----------------------------------------------------------
# REWORTH_ENV=production  -> secure defaults (set automatically by render.yaml)
# anything else           -> local/demo defaults
IS_PROD = os.environ.get("REWORTH_ENV", "development").strip().lower() == "production"
# Direct (email-only) password reset + the "Use demo admin" shortcut are an OPT-IN demo
# convenience (REWORTH_DEMO_MODE=1). They are OFF by default, locally and in production.
DEMO_MODE = os.environ.get("REWORTH_DEMO_MODE") == "1"
MIN_PASSWORD = 8

DEMO_ADMIN_EMAIL = os.environ.get("REWORTH_ADMIN_EMAIL", "admin@reworth.local").strip().lower()
_ENV_ADMIN_PASSWORD = os.environ.get("REWORTH_ADMIN_PASSWORD")
DEMO_ADMIN_PASSWORD = _ENV_ADMIN_PASSWORD or "ReWorth@123"

_secret = os.environ.get("REWORTH_SECRET_KEY")
if IS_PROD and not _secret:
    raise RuntimeError("REWORTH_SECRET_KEY must be set when REWORTH_ENV=production.")

app = Flask(__name__)
app.secret_key = _secret or "dev-only-change-this-key"
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=IS_PROD,
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    MAX_CONTENT_LENGTH=64 * 1024,
)
if IS_PROD:
    # Render terminates TLS at a proxy; trust its forwarded headers.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

CATEGORIES = [
    "Mobile / Tablet", "Computer / Laptop", "TV / Monitor", "Home appliance",
    "Furniture", "Clothing", "Other"
]

EXPECTED_LIFE = {
    "Mobile / Tablet": 5,
    "Computer / Laptop": 6,
    "TV / Monitor": 8,
    "Home appliance": 10,
    "Furniture": 12,
    "Clothing": 4,
    "Other": 7,
}

PROBLEM_SEVERITY = {
    "Minor / occasional issue": 1,
    "Performance has become poor": 2,
    "Physical damage": 3,
    "Doesn't turn on": 4,
    "Battery / power issue": 3,
    "Display / screen issue": 3,
    "Overheating": 3,
    "Strange noise": 2,
    "Not sure": 3,
    "Other": 3,
}

REPAIRABILITY = {
    "Minor / occasional issue": 4,
    "Performance has become poor": 4,
    "Physical damage": 2,
    "Doesn't turn on": 2,
    "Battery / power issue": 3,
    "Display / screen issue": 3,
    "Overheating": 3,
    "Strange noise": 3,
    "Not sure": 1,
    "Other": 2,
}


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def add_column_if_missing(conn, table, column, definition):
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.DatabaseError:
        pass
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT NOT NULL UNIQUE,
        expires_at TEXT NOT NULL,
        used INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        category TEXT NOT NULL,
        age INTEGER NOT NULL,
        condition TEXT NOT NULL,
        problem TEXT NOT NULL,
        repair_history TEXT NOT NULL,
        repair_cost REAL,
        replacement_cost REAL,
        decision TEXT NOT NULL,
        score INTEGER NOT NULL,
        reason TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    # Safe migration for the earlier ReWorth database version.
    migrations = {
        "usage_frequency": "TEXT",
        "functional_condition": "TEXT",
        "cosmetic_condition": "TEXT",
        "missing_parts": "TEXT",
        "problem_type": "TEXT",
        "incident": "TEXT",
        "repair_cost_known": "INTEGER DEFAULT 1",
        "replacement_cost_known": "INTEGER DEFAULT 1",
        "confidence": "TEXT DEFAULT 'Moderate'",
        "quality": "INTEGER DEFAULT 0",
        "score_condition": "INTEGER DEFAULT 0",
        "score_age": "INTEGER DEFAULT 0",
        "score_problem": "INTEGER DEFAULT 0",
        "score_history": "INTEGER DEFAULT 0",
        "score_economics": "INTEGER DEFAULT 0",
        "score_repairability": "INTEGER DEFAULT 0",
        "next_step": "TEXT DEFAULT ''",
        "explanation": "TEXT DEFAULT ''",
    }
    add_column_if_missing(conn, "users", "role", "TEXT NOT NULL DEFAULT 'user'")
    for column, definition in migrations.items():
        add_column_if_missing(conn, "assessments", column, definition)

    conn.commit()
    conn.close()
    ensure_demo_admin()


def ensure_demo_admin():
    """Create the administrator account.

    Local/demo: a default admin (admin@reworth.local) is created if missing.
    Production: an admin is created ONLY when REWORTH_ADMIN_PASSWORD is provided.
    If the variable is provided, the admin password is synchronised to it on start-up,
    so the owner can rotate it by changing the environment variable.
    """
    if IS_PROD and not _ENV_ADMIN_PASSWORD:
        print("[ReWorth] No REWORTH_ADMIN_PASSWORD set: no admin account was created.")
        return
    if IS_PROD and len(DEMO_ADMIN_PASSWORD) < MIN_PASSWORD:
        print("[ReWorth] REWORTH_ADMIN_PASSWORD is too short: admin not created.")
        return
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (DEMO_ADMIN_EMAIL,)).fetchone()
    now = datetime.now().isoformat(timespec="seconds")
    if existing:
        if _ENV_ADMIN_PASSWORD:
            conn.execute("UPDATE users SET role = 'admin', password_hash = ? WHERE id = ?",
                         (generate_password_hash(DEMO_ADMIN_PASSWORD), existing["id"]))
        else:
            conn.execute("UPDATE users SET role = 'admin' WHERE id = ?", (existing["id"],))
    else:
        conn.execute(
            "INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, 'admin', ?)",
            ("ReWorth Admin", DEMO_ADMIN_EMAIL, generate_password_hash(DEMO_ADMIN_PASSWORD), now))
    conn.commit()
    conn.close()


def csv_safe(value):
    """Neutralise spreadsheet formula injection in exported CSV cells."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


# --- Security helpers: CSRF, headers, login throttling ---------------------
_FAILED = {}  # key -> list[timestamps]; in-memory, per worker
MAX_FAILS, WINDOW = 5, 15 * 60


def throttled(key):
    now = time.time()
    _FAILED[key] = [t for t in _FAILED.get(key, []) if now - t < WINDOW]
    return len(_FAILED[key]) >= MAX_FAILS


def record_fail(key):
    _FAILED.setdefault(key, []).append(time.time())


def client_key(email):
    return f"{request.remote_addr}|{email}"


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token
app.jinja_env.globals["DEMO_MODE"] = DEMO_MODE


@app.before_request
def csrf_protect():
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
        if not sent or not secrets.compare_digest(sent, session.get("_csrf", "")):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Security token missing or expired. Please refresh the page and try again."}), 400
            flash("Your session expired. Please try again.", "error")
            return redirect(url_for("home"))


@app.after_request
def security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if IS_PROD:
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return resp


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404, message="That page could not be found."), 404


@app.errorhandler(413)
def too_large(_e):
    return render_template("error.html", code=413, message="That request was too large."), 413


@app.errorhandler(500)
def server_error(_e):
    return render_template("error.html", code=500, message="Something went wrong on our side. Please try again."), 500


def clean_text(value, fallback=""):
    return str(value or "").strip()


def calculate_recommendation(data):
    """Transparent decision-support engine. It does not diagnose faults or invent prices."""
    age = data["age"]
    category = data["category"]
    condition = data["condition"]
    functional = data["functional_condition"]
    cosmetic = data["cosmetic_condition"]
    problem_type = data["problem_type"]
    repair_history = data["repair_history"]
    usage = data["usage_frequency"]
    repair_cost = data["repair_cost"]
    replacement_cost = data["replacement_cost"]

    expected = EXPECTED_LIFE.get(category, EXPECTED_LIFE["Other"])
    reasons = []
    strengths = []
    cautions = []

    # Start from a neutral 50 and calculate independent factors.
    score = 50

    condition_points = {"Excellent": 16, "Good": 10, "Fair": 2, "Poor": -12}.get(condition, 0)
    functional_points = {"Works normally": 12, "Works with problems": 4, "Barely works": -4, "Does not work": -10}.get(functional, 0)
    cosmetic_points = {"Like new": 3, "Minor wear": 2, "Visible wear": 0, "Major damage": -3}.get(cosmetic, 0)
    score += condition_points + functional_points + cosmetic_points
    if condition in ("Excellent", "Good"):
        strengths.append("The overall condition is still reasonably strong.")
    if functional == "Does not work":
        cautions.append("The product currently has a major functional problem.")

    life_ratio = age / max(expected, 1)
    if life_ratio <= 0.35:
        age_points = 12
        reasons.append("The product is relatively young for its category.")
    elif life_ratio <= 0.65:
        age_points = 7
        reasons.append("The product is around the middle of its expected useful-life range.")
    elif life_ratio <= 0.90:
        age_points = 1
        cautions.append("The product is getting closer to the typical end of its useful-life range.")
    else:
        age_points = -10
        cautions.append("The product is older than the typical useful-life range used by ReWorth.")
    score += age_points

    usage_points = {"Rarely": 2, "Sometimes": 1, "Daily": 0, "Very heavily": -2}.get(usage, 0)
    score += usage_points

    severity = PROBLEM_SEVERITY.get(problem_type, 3)
    repairability = REPAIRABILITY.get(problem_type, 2)
    problem_points = {1: 9, 2: 5, 3: 0, 4: -5}.get(severity, 0)
    repairability_points = {1: -6, 2: 0, 3: 5, 4: 8}.get(repairability, 0)
    score += problem_points + repairability_points

    if severity <= 2:
        strengths.append("The reported problem is relatively limited or performance-related.")
    elif problem_type == "Not sure":
        cautions.append("The exact fault is not known, so ReWorth cannot reliably judge repairability.")
    else:
        cautions.append("The reported problem may require a proper diagnosis before a repair decision.")

    history_points = {"Never repaired": 5, "Repaired once": 0, "Repaired multiple times": -10}.get(repair_history, 0)
    score += history_points
    if repair_history == "Never repaired":
        strengths.append("There is no history of repeated repairs.")
    elif repair_history == "Repaired multiple times":
        cautions.append("Repeated repairs suggest increasing maintenance needs.")

    economics_points = 0
    economics_known = repair_cost is not None and replacement_cost is not None and replacement_cost > 0
    if economics_known:
        ratio = repair_cost / replacement_cost
        if ratio <= 0.30:
            economics_points = 18
            strengths.append("The estimated repair cost is much lower than replacement.")
        elif ratio <= 0.55:
            economics_points = 11
            strengths.append("The estimated repair cost is meaningfully below replacement.")
        elif ratio <= 0.75:
            economics_points = 4
            reasons.append("Repair is still cheaper than replacement, but the gap is smaller.")
        elif ratio <= 0.90:
            economics_points = -6
            cautions.append("Repair is getting close to the replacement cost.")
        else:
            economics_points = -18
            cautions.append("Repair is estimated to cost almost as much as, or more than, replacement.")
        score += economics_points
    else:
        reasons.append("Cost estimates were not provided, so the score does not assume a price.")

    score = max(0, min(100, round(score)))

    # Confidence is based on information quality, not on how high the score is.
    known_fields = 0
    total_fields = 7
    for key in ["age", "condition", "functional_condition", "problem_type", "repair_history", "usage_frequency", "category"]:
        if data.get(key) not in (None, "", "Not sure"):
            known_fields += 1
    quality = round((known_fields / total_fields) * 100)
    if economics_known:
        quality = min(100, quality + 10)
    if data.get("problem_description"):
        quality = min(100, quality + 5)

    unknown_fault = problem_type == "Not sure" or functional == "Does not work"
    severe_unknown = unknown_fault and repair_cost is None

    if severe_unknown:
        decision = "Diagnosis Required"
        confidence = "Low"
        score = min(score, 55)
        next_step = "Get the product diagnosed and obtain an estimated repair cost before deciding whether to repair or replace it."
        reasons.insert(0, "There is not enough information to make a reliable repair-or-replace call yet.")
    elif not economics_known and quality < 70:
        decision = "Diagnosis Required"
        confidence = "Low"
        next_step = "Add a little more information or get a repair estimate, then reassess."
        reasons.insert(0, "The available information is too limited for a confident decision.")
    else:
        if economics_known and repair_cost >= replacement_cost * 1.05 and score < 55:
            decision = "Replace"
        elif economics_known and repair_cost >= replacement_cost * 0.90 and score < 70:
            decision = "Recycle" if age >= expected * 0.9 or repair_history == "Repaired multiple times" else "Replace"
        elif economics_known and repair_cost >= replacement_cost * 0.90:
            # Healthy product, but repair costs ~ a new one: repairing is not worth it; keep using as-is.
            decision = "Reuse"
        elif score >= 68 and repairability >= 2:
            decision = "Repair"
        elif score >= 52:
            decision = "Reuse"
        elif score >= 38:
            decision = "Donate"
        else:
            decision = "Recycle"

        confidence = "High" if quality >= 85 and (economics_known or score >= 65) else "Moderate"
        next_step = {
            "Repair": "Get a repair estimate and confirm the repair comes with a reasonable expected service life.",
            "Reuse": "Keep using it if it remains safe and functional, and consider basic maintenance to extend its life.",
            "Donate": "If it still works reliably, consider donating it after removing personal data and checking its condition.",
            "Recycle": "If repair is not practical, use an appropriate recycling or responsible disposal route.",
            "Replace": "Compare durable replacement options, then recycle or responsibly dispose of the old product where possible.",
        }[decision]

    explanation_parts = []
    if strengths:
        explanation_parts.append("Positive signals: " + " ".join(strengths[:3]))
    if cautions:
        explanation_parts.append("Things to consider: " + " ".join(cautions[:3]))
    if reasons:
        explanation_parts.append("Assessment: " + " ".join(reasons[:3]))
    explanation = " ".join(explanation_parts)

    return {
        "decision": decision,
        "score": score,
        "confidence": confidence,
        "quality": quality,
        "reason": explanation,
        "next_step": next_step,
        "components": {
            "condition": condition_points + functional_points + cosmetic_points,
            "age": age_points,
            "problem": problem_points,
            "history": history_points,
            "economics": economics_points,
            "repairability": repairability_points,
        },
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/assess")
def assess():
    if "user_id" not in session:
        flash("Create an account or log in if you want to save your assessment history.", "info")
    return render_template("assess.html", categories=CATEGORIES)


@app.route("/register", methods=["POST"])
def register():
    name = clean_text(request.form.get("name"))
    email = clean_text(request.form.get("email")).lower()
    password = request.form.get("password", "")
    if not name or "@" not in email or len(password) < MIN_PASSWORD:
        flash("Please enter your name, a valid email, and a password of at least 8 characters.", "error")
        return redirect(url_for("home"))
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, 'user', ?)",
                     (name, email, generate_password_hash(password), datetime.now().isoformat(timespec="seconds")))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        flash("An account with that email already exists. Try logging in.", "error")
        return redirect(url_for("home"))
    user = conn.execute("SELECT id, name, role FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    session.clear()
    session.permanent = True
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_role"] = user["role"]
    flash("Welcome to ReWorth. Your account is ready.", "success")
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["POST"])
def login():
    email = clean_text(request.form.get("email")).lower()
    password = request.form.get("password", "")
    key = client_key(email)
    if throttled(key):
        flash("Too many failed attempts. Please wait 15 minutes and try again.", "error")
        return redirect(url_for("home"))
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if not user or not check_password_hash(user["password_hash"], password):
        record_fail(key)
        flash("Email or password is incorrect.", "error")
        return redirect(url_for("home"))
    session.clear()
    session.permanent = True
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_role"] = user["role"]
    flash(f"Welcome back, {user['name'].split()[0]}!", "success")
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))



@app.route("/account")
def account():
    if "user_id" not in session:
        return redirect(url_for("home"))
    conn = get_db()
    user = conn.execute("SELECT id, name, email, role, created_at FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()
    if not user:
        session.clear()
        flash("Your account could not be found.", "error")
        return redirect(url_for("home"))
    return render_template("account.html", user=user)


@app.route("/account/profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return redirect(url_for("home"))
    name = clean_text(request.form.get("name"))
    email = clean_text(request.form.get("email")).lower()
    if not name or "@" not in email:
        flash("Please enter a valid name and email.", "error")
        return redirect(url_for("account"))
    conn = get_db()
    conflict = conn.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, session["user_id"])).fetchone()
    if conflict:
        conn.close()
        flash("That email is already linked to another account.", "error")
        return redirect(url_for("account"))
    conn.execute("UPDATE users SET name = ?, email = ? WHERE id = ?", (name, email, session["user_id"]))
    conn.commit()
    conn.close()
    session["user_name"] = name
    flash("Your account details were updated.", "success")
    return redirect(url_for("account"))


@app.route("/account/password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return redirect(url_for("home"))
    current = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")
    conn = get_db()
    user = conn.execute("SELECT password_hash FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if not user or not check_password_hash(user["password_hash"], current):
        conn.close()
        flash("Your current password is incorrect.", "error")
        return redirect(url_for("account"))
    if len(new_password) < MIN_PASSWORD or new_password != confirm:
        conn.close()
        flash("New passwords must match and contain at least 8 characters.", "error")
        return redirect(url_for("account"))
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new_password), session["user_id"]))
    conn.commit()
    conn.close()
    flash("Your password has been changed.", "success")
    return redirect(url_for("account"))


@app.route("/account/export.csv")
def account_export():
    if "user_id" not in session:
        return redirect(url_for("home"))
    conn = get_db()
    rows = conn.execute("""
        SELECT product_name, category, age, condition, functional_condition,
               problem_type, repair_history, repair_cost, replacement_cost,
               decision, score, confidence, quality, created_at
        FROM assessments WHERE user_id = ? ORDER BY id DESC
    """, (session["user_id"],)).fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Product", "Category", "Age", "Condition", "Functional Condition", "Problem", "Repair History", "Repair Cost", "Replacement Cost", "Decision", "Score", "Confidence", "Information Quality", "Created At"])
    for row in rows:
        writer.writerow([csv_safe(v) for v in row])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=reworth_my_assessments.csv"})


@app.route("/account/delete", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        return redirect(url_for("home"))
    password = request.form.get("password", "")
    conn = get_db()
    user = conn.execute("SELECT password_hash, role FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        conn.close()
        flash("The password was incorrect, so the account was not deleted.", "error")
        return redirect(url_for("account"))
    if user["role"] == "admin":
        conn.close()
        flash("The demo administrator cannot be deleted from Account Settings.", "error")
        return redirect(url_for("account"))
    conn.execute("DELETE FROM users WHERE id = ?", (session["user_id"],))
    conn.commit()
    conn.close()
    session.clear()
    flash("Your ReWorth account and saved assessments have been deleted.", "info")
    return redirect(url_for("home"))


def make_reset_token(conn, user_id, minutes=30):
    """Invalidate older tokens and create a new single-use reset token."""
    conn.execute("UPDATE password_reset_tokens SET used = 1 WHERE user_id = ? AND used = 0", (user_id,))
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    conn.execute(
        "INSERT INTO password_reset_tokens (user_id, token, expires_at, used, created_at) VALUES (?, ?, ?, 0, ?)",
        (user_id, token, (now + timedelta(minutes=minutes)).isoformat(timespec="seconds"), now.isoformat(timespec="seconds")))
    return token


def send_reset_email(to_email, link):
    """Send via SMTP when REWORTH_SMTP_HOST is configured. Returns True if sent."""
    host = os.environ.get("REWORTH_SMTP_HOST")
    if not host:
        # No mail server configured: print the link to the server console/logs
        # (VS Code terminal locally, Render > Logs when deployed). Only the owner sees it.
        print(f"\n[ReWorth] PASSWORD RESET LINK for {to_email}:\n{link}\n", flush=True)
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = "Reset your ReWorth password"
        msg["From"] = os.environ.get("REWORTH_SMTP_FROM", os.environ.get("REWORTH_SMTP_USER", "no-reply@reworth.local"))
        msg["To"] = to_email
        msg.set_content(f"Use this link within 30 minutes to reset your ReWorth password:\n\n{link}\n\n"
                        "If you did not request this, ignore this email.")
        with smtplib.SMTP(host, int(os.environ.get("REWORTH_SMTP_PORT", "587")), timeout=10) as smtp:
            smtp.starttls()
            if os.environ.get("REWORTH_SMTP_USER"):
                smtp.login(os.environ["REWORTH_SMTP_USER"], os.environ.get("REWORTH_SMTP_PASSWORD", ""))
            smtp.send_message(msg)
        return True
    except Exception as exc:  # never reveal mail errors to the visitor
        print(f"[ReWorth] reset email failed: {exc}")
        return False


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Password recovery.

    Production (default): emails a single-use, 30-minute link (SMTP) -- or an administrator
    can generate the link from Admin > Users. The response never reveals whether an email exists.
    Local demo (DEMO_MODE): the user may reset directly with just their email. This is never
    allowed for administrator accounts.
    """
    if request.method == "POST":
        email = clean_text(request.form.get("email")).lower()
        if not email:
            flash("Enter the email registered with your ReWorth account.", "error")
            return render_template("forgot_password.html")

        if DEMO_MODE:
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            if len(password) < MIN_PASSWORD:
                flash(f"Your new password must contain at least {MIN_PASSWORD} characters.", "error")
                return render_template("forgot_password.html")
            if password != confirm:
                flash("The passwords do not match. Please try again.", "error")
                return render_template("forgot_password.html")
            conn = get_db()
            user = conn.execute("SELECT id, role FROM users WHERE email = ?", (email,)).fetchone()
            if user and user["role"] != "admin":
                conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                             (generate_password_hash(password), user["id"]))
                conn.execute("UPDATE password_reset_tokens SET used = 1 WHERE user_id = ? AND used = 0", (user["id"],))
                conn.commit()
                conn.close()
                flash("Password changed successfully. You can now log in with your new password.", "success")
                return redirect(url_for("home"))
            conn.close()
            flash("That account cannot be reset here. Check the email or contact the administrator.", "error")
            return render_template("forgot_password.html")

        # Production flow
        key = client_key("reset:" + email)
        if not throttled(key):
            record_fail(key)  # counts every request, so the endpoint cannot be spammed
            conn = get_db()
            user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if user:
                token = make_reset_token(conn, user["id"])
                conn.commit()
                send_reset_email(email, url_for("reset_password", token=token, _external=True))
            conn.close()
        flash("If that email is registered, a reset link has been sent. If you do not receive it, "
              "ask the ReWorth administrator for a reset link.", "info")
        return redirect(url_for("home"))
    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    # Kept for compatibility with any local reset links generated by older versions.
    conn = get_db()
    row = conn.execute("SELECT id, user_id, expires_at, used FROM password_reset_tokens WHERE token = ?", (token,)).fetchone()
    valid = bool(row and not row["used"] and datetime.fromisoformat(row["expires_at"]) > datetime.now())
    if request.method == "POST" and valid:
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(password) < MIN_PASSWORD or password != confirm:
            conn.close()
            flash("Passwords must match and contain at least 8 characters.", "error")
            return redirect(url_for("reset_password", token=token))
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(password), row["user_id"]))
        conn.execute("UPDATE password_reset_tokens SET used = 1 WHERE id = ?", (row["id"],))
        conn.commit()
        conn.close()
        flash("Your password has been reset. You can now log in.", "success")
        return redirect(url_for("home"))
    conn.close()
    return render_template("reset_password.html", valid=valid)


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("home"))
    conn = get_db()
    rows = conn.execute("SELECT * FROM assessments WHERE user_id = ? ORDER BY id DESC", (session["user_id"],)).fetchall()
    conn.close()
    counts = {key: 0 for key in ["Repair", "Reuse", "Donate", "Recycle", "Replace", "Diagnosis Required"]}
    for row in rows:
        counts[row["decision"]] = counts.get(row["decision"], 0) + 1
    return render_template("dashboard.html", assessments=rows, counts=counts)


@app.route("/api/assess", methods=["POST"])
def api_assess():
    data = request.get_json(silent=True) or request.form
    try:
        age = int(data.get("age", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Please enter a valid product age."}), 400

    if age < 0 or age > 100:
        return jsonify({"error": "Product age should be between 0 and 100 years."}), 400

    required = ["product_name", "category", "condition", "functional_condition", "cosmetic_condition",
                "problem_type", "repair_history", "usage_frequency"]
    if any(not clean_text(data.get(field)) for field in required):
        return jsonify({"error": "Please complete the required assessment fields."}), 400

    def optional_cost(field):
        value = clean_text(data.get(field))
        if value == "":
            return None
        try:
            number = float(value)
        except ValueError:
            raise ValueError
        if number < 0:
            raise ValueError
        return number

    try:
        repair_cost = optional_cost("repair_cost")
        replacement_cost = optional_cost("replacement_cost")
    except ValueError:
        return jsonify({"error": "Costs must be valid non-negative numbers, or left blank if unknown."}), 400

    if clean_text(data.get("category")) not in CATEGORIES:
        return jsonify({"error": "Please choose a valid product category."}), 400
    if len(clean_text(data.get("product_name"))) > 120 or len(clean_text(data.get("problem_description"))) > 1000 \
            or len(clean_text(data.get("missing_parts"))) > 300:
        return jsonify({"error": "One of the text fields is too long."}), 400
    if (repair_cost is not None and repair_cost > 1e9) or (replacement_cost is not None and replacement_cost > 1e9):
        return jsonify({"error": "Costs must be realistic amounts."}), 400
    if replacement_cost is not None and replacement_cost <= 0:
        return jsonify({"error": "Replacement cost must be greater than ₹0, or left blank if unknown."}), 400

    clean = {
        "product_name": clean_text(data.get("product_name")),
        "category": clean_text(data.get("category")),
        "age": age,
        "condition": clean_text(data.get("condition")),
        "functional_condition": clean_text(data.get("functional_condition")),
        "cosmetic_condition": clean_text(data.get("cosmetic_condition")),
        "problem_type": clean_text(data.get("problem_type")),
        "problem_description": clean_text(data.get("problem_description")),
        "incident": clean_text(data.get("incident")),
        "repair_history": clean_text(data.get("repair_history")),
        "usage_frequency": clean_text(data.get("usage_frequency")),
        "missing_parts": clean_text(data.get("missing_parts")),
        "repair_cost": repair_cost,
        "replacement_cost": replacement_cost,
    }

    result = calculate_recommendation(clean)

    if "user_id" in session:
        conn = get_db()
        conn.execute("""
            INSERT INTO assessments
            (user_id, product_name, category, age, condition, problem, repair_history,
             repair_cost, replacement_cost, decision, score, reason, created_at,
             usage_frequency, functional_condition, cosmetic_condition, missing_parts,
             problem_type, incident, repair_cost_known, replacement_cost_known,
             confidence, quality, score_condition, score_age, score_problem,
             score_history, score_economics, score_repairability, next_step, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"], clean["product_name"], clean["category"], clean["age"], clean["condition"],
            clean["problem_description"] or clean["problem_type"], clean["repair_history"],
            (clean["repair_cost"] if clean["repair_cost"] is not None else 0),
            (clean["replacement_cost"] if clean["replacement_cost"] is not None else 0), result["decision"], result["score"], result["reason"],
            datetime.now().isoformat(timespec="seconds"), clean["usage_frequency"], clean["functional_condition"],
            clean["cosmetic_condition"], clean["missing_parts"], clean["problem_type"], clean["incident"],
            int(clean["repair_cost"] is not None), int(clean["replacement_cost"] is not None), result["confidence"],
            result["quality"], result["components"]["condition"], result["components"]["age"], result["components"]["problem"],
            result["components"]["history"], result["components"]["economics"], result["components"]["repairability"],
            result["next_step"], result["reason"]
        ))
        conn.commit()
        conn.close()

    return jsonify({
        "decision": result["decision"],
        "score": result["score"],
        "confidence": result["confidence"],
        "quality": result["quality"],
        "reason": result["reason"],
        "next_step": result["next_step"],
        "components": result["components"],
        "saved": "user_id" in session,
    })



def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        refresh_session_role()
        if session.get("user_role") != "admin":
            if "user_id" in session:
                flash("You do not have permission to open the admin area.", "error")
                return redirect(url_for("dashboard"))
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


def refresh_session_role():
    if "user_id" not in session:
        return
    conn = get_db()
    user = conn.execute("SELECT name, role FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()
    if user:
        session["user_name"] = user["name"]
        session["user_role"] = user["role"]
    else:
        session.clear()


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("user_role") == "admin":
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        email = clean_text(request.form.get("email")).lower()
        password = request.form.get("password", "")
        key = client_key("admin:" + email)
        if throttled(key):
            flash("Too many failed attempts. Please wait 15 minutes and try again.", "error")
            return render_template("admin_login.html")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if not user or user["role"] != "admin" or not check_password_hash(user["password_hash"], password):
            record_fail(key)
            flash("Admin email or password is incorrect.", "error")
            return render_template("admin_login.html")
        session.clear()
        session.permanent = True
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_role"] = "admin"
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_login.html")


@app.route("/admin")
@admin_required
def admin_dashboard():
    decision_filter = clean_text(request.args.get("decision"))
    category_filter = clean_text(request.args.get("category"))
    search = clean_text(request.args.get("q"))

    conn = get_db()
    totals = {
        "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "assessments": conn.execute("SELECT COUNT(*) FROM assessments").fetchone()[0],
        "admins": conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0],
        "avg_score": conn.execute("SELECT ROUND(AVG(score), 1) FROM assessments").fetchone()[0] or 0,
        "low_confidence": conn.execute("SELECT COUNT(*) FROM assessments WHERE confidence = 'Low'").fetchone()[0],
    }
    decisions = ["Repair", "Reuse", "Donate", "Recycle", "Replace", "Diagnosis Required"]
    decision_counts = {d: 0 for d in decisions}
    for row in conn.execute("SELECT decision, COUNT(*) AS total FROM assessments GROUP BY decision"):
        decision_counts[row["decision"]] = row["total"]
    category_counts = conn.execute("SELECT category, COUNT(*) AS total FROM assessments GROUP BY category ORDER BY total DESC").fetchall()

    where = []
    params = []
    if decision_filter:
        where.append("a.decision = ?")
        params.append(decision_filter)
    if category_filter:
        where.append("a.category = ?")
        params.append(category_filter)
    if search:
        where.append("(a.product_name LIKE ? OR u.name LIKE ? OR u.email LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    assessments = conn.execute(f"""
        SELECT a.*, u.name AS user_name, u.email AS user_email
        FROM assessments a JOIN users u ON u.id = a.user_id
        {where_sql}
        ORDER BY a.id DESC LIMIT 100
    """, params).fetchall()
    users = conn.execute("SELECT id, name, email, role, created_at FROM users ORDER BY id DESC LIMIT 12").fetchall()
    categories = [row["category"] for row in conn.execute("SELECT DISTINCT category FROM assessments ORDER BY category")]
    conn.close()

    return render_template(
        "admin_dashboard.html",
        totals=totals,
        decision_counts=decision_counts,
        category_counts=category_counts,
        assessments=assessments,
        users=users,
        categories=categories,
        decisions=decisions,
        filters={"decision": decision_filter, "category": category_filter, "q": search},
    )


@app.route("/admin/assessment/<int:assessment_id>")
@admin_required
def admin_assessment(assessment_id):
    conn = get_db()
    row = conn.execute("""
        SELECT a.*, u.name AS user_name, u.email AS user_email
        FROM assessments a JOIN users u ON u.id = a.user_id
        WHERE a.id = ?
    """, (assessment_id,)).fetchone()
    conn.close()
    if not row:
        flash("Assessment not found.", "error")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_assessment.html", row=row)


@app.route("/admin/users")
@admin_required
def admin_users():
    q = clean_text(request.args.get("q"))
    conn = get_db()
    if q:
        like = f"%{q}%"
        users = conn.execute("SELECT id, name, email, role, created_at FROM users WHERE name LIKE ? OR email LIKE ? ORDER BY id DESC", (like, like)).fetchall()
    else:
        users = conn.execute("SELECT id, name, email, role, created_at FROM users ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin_users.html", users=users, q=q)


@app.route("/admin/users/<int:user_id>/role", methods=["POST"])
@admin_required
def admin_change_role(user_id):
    new_role = clean_text(request.form.get("role"))
    if new_role not in {"user", "admin"}:
        flash("Invalid role.", "error")
        return redirect(url_for("admin_users"))
    if user_id == session.get("user_id") and new_role != "admin":
        flash("You cannot remove your own admin access.", "error")
        return redirect(url_for("admin_users"))
    conn = get_db()
    user = conn.execute("SELECT id, name FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("admin_users"))
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()
    flash(f"{user['name']} is now {new_role}.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/reset-link", methods=["POST"])
@admin_required
def admin_reset_link(user_id):
    conn = get_db()
    user = conn.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("admin_users"))
    token = make_reset_token(conn, user["id"])
    conn.commit()
    conn.close()
    link = url_for("reset_password", token=token, _external=True)
    flash(f"Reset link for {user['email']} (valid 30 minutes, single use): {link}", "info")
    return redirect(url_for("admin_users"))


@app.route("/admin/export.csv")
@admin_required
def admin_export():
    decision_filter = clean_text(request.args.get("decision"))
    category_filter = clean_text(request.args.get("category"))
    search = clean_text(request.args.get("q"))
    where = []
    params = []
    if decision_filter:
        where.append("a.decision = ?")
        params.append(decision_filter)
    if category_filter:
        where.append("a.category = ?")
        params.append(category_filter)
    if search:
        where.append("(a.product_name LIKE ? OR u.name LIKE ? OR u.email LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    conn = get_db()
    rows = conn.execute(f"""
        SELECT a.id, u.name AS user_name, u.email AS user_email, a.product_name,
               a.category, a.age, a.condition, a.problem_type, a.decision,
               a.score, a.confidence, a.created_at
        FROM assessments a JOIN users u ON u.id = a.user_id
        {where_sql} ORDER BY a.id DESC
    """, params).fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "User", "Email", "Product", "Category", "Age", "Condition", "Problem", "Decision", "Score", "Confidence", "Created At"])
    for row in rows:
        writer.writerow([csv_safe(v) for v in row])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=reworth_assessments.csv"})


@app.route("/health")
def health():
    return {"status": "ok", "app": "ReWorth", "engine": "v2-smart-rule-based"}


def create_admin_from_cli():
    print("\nReWorth Admin Setup")
    print("Create an administrator for the local project.\n")
    name = input("Admin name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass.getpass("Admin password (8+ characters): ")
    if not name or "@" not in email or len(password) < MIN_PASSWORD:
        print("Invalid details. Use a name, valid email and password of at least 8 characters.")
        return 1
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.execute("UPDATE users SET name = ?, password_hash = ?, role = 'admin' WHERE id = ?",
                     (name, generate_password_hash(password), existing["id"]))
        message = "Existing account promoted to admin."
    else:
        conn.execute("INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, 'admin', ?)",
                     (name, email, generate_password_hash(password), datetime.now().isoformat(timespec="seconds")))
        message = "Admin account created."
    conn.commit()
    conn.close()
    print(message)
    print("Open /admin in the ReWorth app and use these credentials.")
    return 0


init_db()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "create-admin":
        raise SystemExit(create_admin_from_cli())
    app.run(host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", "5000")),
            debug=os.environ.get("FLASK_DEBUG") == "1")
