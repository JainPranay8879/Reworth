# ReWorth — Project Proposal & Feasibility Study

**Academic Title:** RepairBeforeReplace — Intelligent Product Decision Platform  
**Tagline:** Know its worth before you replace it.

## 1. Overview
ReWorth is a web-based decision-support platform that helps users decide whether an old or damaged product should be **Repair, Reuse, Donate, Recycle, or Replace**. The user enters product age, condition, problem, repair history, estimated repair cost and estimated replacement cost. A transparent rule-based engine evaluates these details and provides a recommendation with an explanation.

## 2. Problem Statement
Users often replace damaged products without systematically comparing repairability, cost, age, condition and previous repair history. There is a need for a simple application that turns these everyday details into a clear, explainable decision.

## 3. Objectives
- Provide a simple product assessment workflow.
- Compare estimated repair and replacement costs.
- Consider age, condition and repair history.
- Generate one of five practical recommendations.
- Explain the recommendation rather than presenting a black-box result.
- Save assessment history for registered users.
- Demonstrate authentication, validation, database integration and testing in a real-world application.

## 4. Scope
### Included
Registration, login/logout, password hashing, product assessment, validation, recommendation engine, recommendation explanation, history, dashboard, SQLite database, backend API, responsive UI, error handling and GitHub-ready project structure.

### Excluded from Version 1
Repair booking, product purchasing, payments, real-time market prices, technician diagnosis, image damage detection and machine learning.

## 5. Target Users
Students, households and general consumers who want to make a more informed decision about old or damaged products.

## 6. Existing vs Proposed Approach
| Existing approach | ReWorth |
|---|---|
| Personal guesswork | Structured assessment |
| Repair/replacement may not be compared | Cost comparison |
| No consistent reasoning | Rule-based score |
| Decision may not be recorded | Assessment history |

## 7. Feasibility Study
### Technical
**Feasible.** Flask, Python, HTML, CSS, JavaScript and SQLite are sufficient. No specialised hardware is required.

### Economic
**Feasible.** The core software stack is free/open-source and the project can be developed on an existing computer.

### Operational
**Feasible.** The workflow is simple: log in → enter product details → assess → read recommendation → review history.

### Schedule
**Feasible.** The work is divided into planning, requirements, design, development, testing and finalisation and fits the planned 60 practical hours.

## 8. Technology Stack
- Frontend: HTML5, CSS3, JavaScript
- Backend: Python + Flask
- Database: SQLite
- Version control: Git/GitHub

## 9. Recommendation Engine
The current engine is deliberately **rule-based**, not AI/ML. It starts from a base score and adjusts it according to condition, repair/replacement cost ratio, age and repair history. The final score is mapped to Repair, Reuse, Donate, Recycle or Replace using explicit thresholds.

## 10. Risks and Mitigation
| Risk | Mitigation |
|---|---|
| Incorrect user input | Server-side validation |
| Recommendation logic error | Test representative scenarios |
| Database failure | Error handling and regular local backups during development |
| Scope creep | Keep Version 1 feature list fixed |
| UI problems on small screens | Responsive CSS and mobile testing |

## 11. Success Criteria
The project is successful when users can register, log in, submit a valid assessment, receive a recommendation with an explanation, and view saved assessments from the dashboard without major errors.

## 12. Conclusion
ReWorth converts a simple everyday question — “Should I replace this?” — into a structured software problem. Its deliberately transparent recommendation logic makes the prototype practical, testable and easy to demonstrate in a viva, while its architecture leaves room for future improvements.
