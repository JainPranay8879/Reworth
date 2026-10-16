# Project Structure

ReWorth/
├── app.py                 # Flask backend, routes, database and recommendation engine
├── requirements.txt       # Python dependencies
├── README.md              # Setup and project explanation
├── VIVA.md                # Viva questions and answers
├── TEST_CASES.md          # Testing checklist
├── PROJECT_STRUCTURE.md   # File-by-file explanation
├── templates/
│   ├── base.html          # Shared navigation, footer and login/register modals
│   ├── index.html         # Home page
│   ├── assess.html        # Product assessment page
│   └── dashboard.html     # User history/dashboard
└── static/
    ├── css/style.css      # Responsive visual design
    └── js/app.js          # Assessment request, result modal and UI interactions

reworth.db is generated automatically after the first run.

- `templates/admin_login.html` — administrator login page
- `templates/admin_dashboard.html` — admin KPIs, decision analytics, filters and recent assessments
- `templates/admin_assessment.html` — full assessment detail and scoring factors
- `templates/admin_users.html` — user search and role management
- `ADMIN_GUIDE.md` — admin setup and usage instructions
