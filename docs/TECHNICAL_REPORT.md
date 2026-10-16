# Technical Report — ReWorth (Mini Project – I)

| Syllabus deliverable | Where it is |
|---|---|
| Project proposal & feasibility | [PROJECT_PROPOSAL.md](PROJECT_PROPOSAL.md) |
| SRS | [SRS.md](SRS.md) |
| SDLC model, WBS, Gantt | [SDLC_PLAN.md](SDLC_PLAN.md) |
| Complete UML set | [UML_DIAGRAMS.md](UML_DIAGRAMS.md) |
| Architecture design | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Working application | `app.py`, `templates/`, `static/` |
| Testing (unit, black-box, integration, bug tracking) | [TEST_REPORT.md](TEST_REPORT.md), `tests/` |
| Performance & security validation | [SECURITY_AND_PERFORMANCE.md](SECURITY_AND_PERFORMANCE.md) |
| Deployment & GitHub | [DEPLOYMENT.md](DEPLOYMENT.md), `render.yaml`, `.github/workflows/ci.yml` |
| User manual & screenshots | [USER_MANUAL.md](USER_MANUAL.md), `screenshots/` |
| Viva preparation | [VIVA.md](VIVA.md) |

## Source-code documentation
| Module / function | Responsibility |
|---|---|
| `init_db`, `get_db`, `add_column_if_missing` | Schema creation, WAL, safe migrations |
| `ensure_demo_admin` | Admin bootstrap (demo defaults locally; env-driven in production) |
| `calculate_recommendation` | Explainable scoring engine; returns decision, score, confidence, quality, factors, reason, next step |
| `csrf_protect`, `security_headers`, `throttled` | Cross-cutting security |
| `/api/assess` | Validation → engine → optional save |
| `register`, `login`, `account*`, `forgot_password`, `reset_password` | Identity and recovery |
| `admin_*` routes + `admin_required` | Administration |
| `make_reset_token`, `send_reset_email` | Single-use recovery links |

## Course-outcome mapping
OC1 SRS + feasibility · OC2 UML + architecture · OC3 auth, validation, error handling · OC4 tests, Git/GitHub, CI · OC5 documentation, demo, performance and security validation.

## Limitations & future work
Rule weights are expert-chosen, not learned; no live prices; SQLite is single-node; add email verification, CSP, MFA, PostgreSQL, and a repair-shop directory.
