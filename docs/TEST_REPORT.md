# Test Report — ReWorth
**Run:** `pytest -v` · 31 tests · **31 passed, 0 failed** · also executed automatically by GitHub Actions on every push (`.github/workflows/ci.yml`).

| Type | File | What it covers |
|---|---|---|
| Unit (white-box) | `tests/test_engine.py` | Engine decisions, blank costs, "Diagnosis Required", repair ≈ replacement cost, old/repeatedly-repaired product, determinism |
| Integration / black-box | `tests/test_app.py` | Validation, register/login/logout, saving & dashboard, admin flows, password reset, DB migration, health |
| Security | `tests/test_app.py` | CSRF, hashing, throttling, XSS escaping, SQL-injection string, role checks, CSV injection, headers, production-mode config |
| Load | `tests/load_test.py` | Concurrent users against a running instance |

## Test cases
| ID | Scenario | Expected | Result |
|---|---|---|---|
| TC-01 | Young product, good condition, cheap repair | Repair or Reuse with explanation | Pass |
| TC-02 | Costs left blank | No price assumed (economics score 0) | Pass |
| TC-03 | Dead laptop, unknown fault, no costs | Diagnosis Required, Low confidence | Pass |
| TC-04 | Repair cost ≈ 93% of replacement | Not "Repair" | Pass (found a bug: engine returned Repair; **fixed**) |
| TC-05 | 12-year-old, repeatedly repaired, poor | Lower score; Recycle/Replace/Donate | Pass |
| TC-06 | Missing required field | 400 + message | Pass |
| TC-07 | Negative age / cost, zero replacement cost, non-numeric age | 400 | Pass |
| TC-08 | Assess while logged out | Result shown, not saved | Pass |
| TC-09 | Assess while logged in | Saved, appears on dashboard | Pass |
| TC-10 | Empty dashboard | Loads without error | Pass |
| TC-11 | Old database opened by new version | Columns auto-added | Pass |
| TC-12 | `/health` | `{"status":"ok"}` | Pass |
| TC-13 | Invalid category / over-long text | 400 | Pass |
| TC-14 | Wrong password, then correct | Error, then redirect to dashboard | Pass |
| TC-15 | 5 failed logins | Account/IP temporarily throttled | Pass |
| TC-16 | POST without CSRF token | Rejected | Pass |
| TC-17 | `<script>` in product name | Escaped on dashboard | Pass |
| TC-18 | Regular user opens `/admin` | Redirected | Pass |
| TC-19 | Admin login, dashboard, users, CSV export | Works | Pass |
| TC-20 | Admin generates reset link; user resets; link reused | Works once, then invalid | Pass |
| TC-21 | Direct reset attempted on admin account | Refused | Pass |
| TC-22 | Production start without secret key | Refuses to start | Pass |
| TC-23 | Production hides demo credentials and direct reset | Confirmed | Pass |
| TC-24 | Default run (no env vars) hides demo button, uses link-based reset | Confirmed | Pass |
| TC-25 | Reset link printed to console when no SMTP | Confirmed | Pass |
| TC-26 | `REWORTH_DEMO_MODE=1` opt-in works and still blocks admin reset | Confirmed | Pass |

## Bugs found and fixed during testing
1. Repair cost ≈ 93% of a new unit still returned **Repair** when other factors scored high → now returns **Reuse** (keep using as-is).
2. Demo admin password was embedded in the admin-login page script even in production → now only in demo mode.
3. Admin password was reset to the default on every restart → now synced only if `REWORTH_ADMIN_PASSWORD` is set.
4. Any account (including admin) could be taken over with just an email address → direct reset removed from production and blocked for admins.
5. "Admin" link shown to logged-in normal users → hidden.

## Bug tracking
Use GitHub Issues with labels `bug`, `enhancement`, `docs`; reference the issue number in commit messages.
