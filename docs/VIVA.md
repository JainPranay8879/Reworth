# ReWorth — Viva Quick Notes

## 1. What is your project?

**ReWorth is a web-based product decision-support platform. It helps users decide whether an old or damaged product should be repaired, reused, donated, recycled or replaced by considering product age, condition, repair history and estimated repair/replacement cost.**

## 2. What real-world problem does it solve?

People often replace products without checking whether repair or reuse is practical. ReWorth gives them a simple structured way to compare the available choices before discarding or replacing a product.

## 3. Why did you choose this topic?

It combines a practical consumer problem with sustainability. It is also a good software-development problem because it needs forms, validation, authentication, database storage, a recommendation engine and a user dashboard.

## 4. Why is it called ReWorth?

Because the system asks a simple question: **what is this product still worth before I replace it?**

## 5. Is this actually AI?

**No. The current version is rule-based.** This is intentional. The recommendation logic is transparent, deterministic and easy to validate. An AI/ML version could be a future enhancement after collecting enough reliable assessment data.

## 6. How does the recommendation work?

The system calculates a score out of 100 using:
- product condition
- repair cost compared with replacement cost
- product age
- repair history

The score and a few rules are then used to recommend Repair, Reuse, Donate, Recycle or Replace.

## 7. Why rule-based instead of AI?

For a student project, a rule-based system is easier to explain, test and debug. It also avoids pretending that a small dataset can make reliable product-life predictions.

## 8. What is the frontend?

HTML, CSS and JavaScript.

## 9. What is the backend?

Python with Flask.

## 10. What database did you use?

SQLite. It is lightweight and does not need a separate database server. If the college specifically requires MySQL, the same logical schema can be migrated.

## 11. Why do you need a backend?

The backend validates data, calculates the recommendation, handles authentication and stores assessment history in the database.

## 12. Why do you need a database?

To persist user accounts and assessment records so the user can return later and see their history.

## 13. What are your main tables?

`users` and `assessments`.

## 14. What is authentication?

Authentication verifies who the user is. In ReWorth, a registered user logs in using email and password.

## 15. How are passwords stored?

Passwords are stored as hashes using Werkzeug's password hashing utilities, not as plain text.

## 16. What is validation?

Validation checks whether input is acceptable before processing it. For example, age cannot be negative and replacement cost must be greater than zero.

## 17. What happens if the user is not logged in?

They can still perform an assessment, but the result is not saved to their personal history. Logged-in users can save and view their assessments.

## 18. What is an API in your project?

`/api/assess` is a backend endpoint that receives assessment data and returns a JSON response containing the decision, score and explanation.

## 19. What is SDLC?

Software Development Life Cycle. In this project it can be explained as:
Problem identification → requirements → design/UML → implementation → testing → deployment → documentation.

## 20. Which SDLC model can you say you followed?

**Iterative development** is a sensible description for this project because the application can be built and improved feature by feature: UI, authentication, assessment engine, database, dashboard, testing and deployment.

## 21. What UML diagrams should you prepare?

For the course outline, prepare:
- Use Case Diagram
- Class Diagram
- Sequence Diagram
- Activity Diagram
- ER Diagram
- Deployment Diagram

## 22. Main actors in the Use Case Diagram?

- User
- Admin (planned/optional extension)

For the current implemented version, the primary actor is the User.

## 23. Main use cases?

Register, Login, Assess Product, View Recommendation, View Assessment History, Logout.

## 24. What is the main limitation?

The recommendation depends on user-provided estimates and simplified rules. It does not automatically inspect a product, know its exact market value, verify repair quotations, or predict its remaining physical life.

## 25. What would you add in the future?

- MySQL/PostgreSQL for larger deployments
- Admin panel for managing categories/rules
- Verified repair-service directory
- Product-specific repair-cost data
- Better analytics
- Optional ML model after collecting a sufficiently large and reliable dataset
- Cloud deployment
- More detailed security controls

## 26. What makes the project different?

It does not simply say “repair it.” It considers five possible next steps and explains the recommendation. The goal is decision support rather than forcing a single action.

## 27. If the examiner asks “Can I trust the score?”

Say:

**“The score should be treated as a decision-support indicator, not a guarantee. The project is transparent about this because the result is based on simplified rules and user-provided information.”**

## 28. If the examiner asks “Why not always repair?”

Say:

**“Repair is not always the best option. If a product is very old, repeatedly repaired, badly damaged, or expensive to repair compared with replacement, another option can be more practical.”**

## 29. If the examiner asks “Why is this a real-world application?”

Say:

**“The problem exists in everyday product disposal and replacement decisions, and the application provides a usable workflow rather than only demonstrating an algorithm.”**

## 30. One-line project explanation

**“ReWorth helps users make a more informed decision about an old or damaged product before they replace it.”**


## Admin Dashboard

**Q: Why did you add an admin dashboard?**
A: It gives authorized administrators a centralized view of users, assessments and recommendation patterns. It also demonstrates role-based access control and makes the system more complete as a real-world application.

**Q: How is admin access protected?**
A: Users have a `role` field. Admin routes use a server-side authorization check, and only accounts with the `admin` role can access them. Passwords are stored as hashes rather than plain text.

**Q: Can a normal user open `/admin`?**
A: No. The server checks the user's role and redirects unauthorized users away from the admin area.

**Q: How do you create an administrator?**
A: The project provides `python app.py create-admin`, which creates or promotes an account to the admin role.


---
## Added in the deployment-ready version
**Q: How did you secure password recovery?**
A: The first version let anyone reset any password with only an email address — fine for a local demo but a takeover risk. In production that path is disabled. Recovery uses single-use, 30-minute tokens sent by email (SMTP) or generated by an administrator, and the response never reveals whether an email is registered. Even in demo mode, administrator accounts cannot be reset that way.

**Q: What is CSRF and how do you prevent it?**
A: A malicious site could make a logged-in user's browser submit a request to ReWorth. Every POST carries a random per-session token that the server checks; requests without it are rejected.

**Q: Why gunicorn and not `app.run`?**
A: The Flask development server is not meant for production. gunicorn runs several worker processes/threads, and `--preload` makes the database setup run once.

**Q: Why does data disappear on Render's free plan?**
A: The free disk is ephemeral. SQLite is a file, so it resets on redeploy. A paid disk (`REWORTH_DB_PATH`) or PostgreSQL would persist it.

**Q: What bug did testing find?**
A: A repair costing ~93% of a new unit was still recommended when the product otherwise scored well. I changed the rule so near-replacement-cost repairs are not recommended.

**Q: Limitations?**
A: Rule weights are expert-chosen, no live prices, SQLite single node, no MFA/email verification/CSP.
