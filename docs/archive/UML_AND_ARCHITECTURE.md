# ReWorth — UML & Architecture Blueprint

This document is the single reference for creating the six required UML diagrams. Every diagram should use the same names and relationships below.

## 1. Use Case Diagram
### Actor
- User

### Use cases
- Register
- Login
- Logout
- Assess Product
- View Recommendation
- View Assessment History
- View Dashboard

### Main relationships
- Assess Product includes Validate Input.
- Assess Product includes Calculate Recommendation.
- Calculate Recommendation includes Generate Explanation.
- Registered User can View Assessment History and Dashboard.
- A visitor can access Product Assessment, but only a logged-in user has the assessment persisted to their account.

## 2. Class Diagram
### User
Attributes:
- id
- name
- email
- password_hash
- created_at

Operations:
- register()
- login()
- logout()

### Assessment
Attributes:
- id
- user_id
- product_name
- category
- age
- condition
- problem
- repair_history
- repair_cost
- replacement_cost
- decision
- score
- reason
- created_at

Operations:
- validate()
- save()

### RecommendationEngine
Operations:
- calculate_recommendation(data)
- calculate_score(data)
- generate_explanation(data)

### Relationships
- One User has many Assessments.
- RecommendationEngine processes assessment input and returns decision, score and explanation.

## 3. Sequence Diagram — Product Assessment
1. User opens assessment page.
2. User enters product details.
3. Browser sends assessment request to Flask API.
4. Flask validates the submitted values.
5. RecommendationEngine calculates score.
6. RecommendationEngine selects decision.
7. RecommendationEngine creates explanation.
8. If the user is logged in, Flask saves the assessment to SQLite.
9. Flask returns decision, score and explanation as JSON.
10. Browser displays the result modal.

## 4. Activity Diagram
Start → Enter product details → Validate input → [Invalid?] Show error → Correct input → Calculate score → Select recommendation → Generate explanation → [Logged in?] Save assessment → Display result → End.

## 5. ER Diagram
### USERS
- id (PK)
- name
- email (UNIQUE)
- password_hash
- created_at

### ASSESSMENTS
- id (PK)
- user_id (FK → USERS.id)
- product_name
- category
- age
- condition
- problem
- repair_history
- repair_cost
- replacement_cost
- decision
- score
- reason
- created_at

Relationship: **USERS 1 : N ASSESSMENTS**.

## 6. Deployment Diagram
### Client
- Web browser

### Application Server
- Python runtime
- Flask application
- HTML/CSS/JavaScript templates/static files
- Recommendation Engine

### Data Layer
- SQLite database (`reworth.db`)

Flow: Browser → Flask Application → Recommendation Engine / SQLite.

## 7. Architecture
ReWorth follows a simple three-layer structure:

**Presentation Layer** — HTML templates, CSS and JavaScript.  
**Application Layer** — Flask routes, validation, authentication and recommendation logic.  
**Data Layer** — SQLite tables for users and assessments.

This structure is small enough for a student project while keeping responsibilities separated.
