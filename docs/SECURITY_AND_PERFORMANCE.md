# Security & Performance Validation — ReWorth

## Security checklist
| Area | Control | Verified by |
|---|---|---|
| Authentication | `scrypt` hashed passwords, min 8 chars, session reset on login | `test_password_is_hashed`, `test_short_password_rejected` |
| Brute force | 5 failures / 15 min throttle on login, admin login and reset requests | `test_login_throttling` |
| CSRF | Per-session token required on every POST (forms + `fetch`) | `test_csrf_blocks_post_without_token` |
| Authorisation | Server-side role check on admin routes; users cannot reach `/admin` | `test_regular_user_cannot_open_admin` |
| Injection | Parameterised SQL; injection strings harmless | `test_sql_injection_string_is_harmless` |
| XSS | Jinja auto-escaping | `test_xss_is_escaped_in_dashboard` |
| CSV injection | Cells starting `= + - @` are prefixed with `'` | `test_csv_formula_injection_neutralised` |
| Recovery | Single-use 30-min tokens; no direct reset in production; admins excluded from demo reset; generic response (no email enumeration) | reset tests |
| Transport/cookies | HSTS, `Secure`/`HttpOnly`/`SameSite` cookies in production | config |
| Headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` | `test_security_headers_present` |
| Secrets | From environment variables; production refuses to start without a secret key | `test_production_mode_*` |
| Input | Whitelisted category, length and range limits, 64 KB body limit | validation tests |

**Known limitations (state these honestly in the viva):** no Content-Security-Policy (templates use inline handlers); throttling is in-memory per worker; SQLite on Render free tier is ephemeral; no email-verification at sign-up; no MFA.

## Basic load test
Command: `python tests/load_test.py http://127.0.0.1:5055 <users> <requests_each>` (mix of `/`, `/assess`, `/health`).
Run on the Flask development server in the build sandbox (indicative only; gunicorn on Render will be at least as good for this workload):

| Concurrent users | Requests | Errors | Throughput | Median | p95 | Max |
|---|---|---|---|---|---|---|
| 20 | 500 | 0 | ~303 req/s | 32 ms | 58 ms | 855 ms |
| 50 | 1000 | 0 | ~282 req/s | 74 ms | 562 ms | 1993 ms |

Result: **no errors**; NFR-02 (p95 < 1 s at 20 users) met. Re-run against your Render URL and paste your numbers here (free instances sleep when idle, so the first request can take ~30–60 s).
