# UML Diagrams — ReWorth
All diagrams are Mermaid and render directly on GitHub.

## 1. Use case diagram
```mermaid
flowchart LR
  G([Guest]):::actor
  U([Registered User]):::actor
  A([Administrator]):::actor
  subgraph ReWorth
    UC1((Assess product))
    UC2((Register))
    UC3((Log in / out))
    UC4((View history))
    UC5((Manage account))
    UC6((Recover password))
    UC7((View analytics))
    UC8((Manage users & roles))
    UC9((Generate reset link))
    UC10((Export CSV))
  end
  G --> UC1 & UC2 & UC3 & UC6
  U --> UC1 & UC3 & UC4 & UC5 & UC6
  A --> UC3 & UC7 & UC8 & UC9 & UC10
  U -. inherits .-> G
  classDef actor fill:#e8f1ec,stroke:#2f6b50;
```

## 2. Class diagram
```mermaid
classDiagram
  class User {
    +int id
    +string name
    +string email
    +string password_hash
    +string role
    +datetime created_at
    +register()
    +login()
    +changePassword()
  }
  class Assessment {
    +int id
    +string product_name
    +string category
    +int age
    +string condition
    +string functional_condition
    +string problem_type
    +string repair_history
    +float repair_cost
    +float replacement_cost
    +string decision
    +int score
    +string confidence
    +int quality
    +string next_step
  }
  class PasswordResetToken {
    +int id
    +string token
    +datetime expires_at
    +bool used
  }
  class RecommendationEngine {
    +calculate_recommendation(data) Result
  }
  class Result {
    +string decision
    +int score
    +string confidence
    +int quality
    +dict components
    +string reason
  }
  class Admin { +viewAnalytics() +exportCSV() +changeRole() +generateResetLink() }
  User "1" --> "0..*" Assessment : owns
  User "1" --> "0..*" PasswordResetToken : requests
  User <|-- Admin
  RecommendationEngine ..> Result : returns
  RecommendationEngine ..> Assessment : evaluates
```

## 3. Sequence diagram — assess a product
```mermaid
sequenceDiagram
  actor U as User
  participant UI as Browser (app.js)
  participant API as Flask /api/assess
  participant E as Engine
  participant DB as SQLite
  U->>UI: fill 4-step form, submit
  UI->>API: POST form + csrf_token
  API->>API: verify CSRF, validate inputs
  alt invalid
    API-->>UI: 400 {error}
  else valid
    API->>E: calculate_recommendation(data)
    E-->>API: decision, score, confidence, factors
    opt user logged in
      API->>DB: INSERT assessment
    end
    API-->>UI: 200 JSON result
    UI-->>U: show decision + explanation
  end
```

## 4. Sequence diagram — password recovery (production)
```mermaid
sequenceDiagram
  actor U as User
  participant App as Flask
  participant DB as SQLite
  participant M as SMTP / Admin
  U->>App: POST /forgot-password (email)
  App->>DB: invalidate old tokens, create token (30 min)
  App->>M: email link (or admin generates link)
  App-->>U: generic "if registered, link sent"
  U->>App: GET /reset-password/<token>
  App->>DB: token valid, unused, not expired?
  U->>App: POST new password
  App->>DB: update hash, mark token used
  App-->>U: success, please log in
```

## 5. Activity diagram — assessment decision flow
```mermaid
flowchart TD
  S([Start]) --> I[Enter product details]
  I --> V{Input valid?}
  V -- No --> I
  V -- Yes --> Q[Compute information quality]
  Q --> SC[Score condition, age, usage,<br/>problem, history, economics]
  SC --> D{Severe unknown fault, or costs<br/>unknown and quality &lt; 70%?}
  D -- Yes --> DR[Diagnosis Required]
  D -- No --> EC{Repair cost ≥ 105%<br/>of replacement<br/>and low score?}
  EC -- Yes --> RP[Replace]
  EC -- No --> E2{Repair cost ≥ 90%<br/>of replacement?}
  E2 -- Yes --> HS{Score ≥ 70?}
  HS -- Yes --> RU[Reuse]
  HS -- No --> RR[Recycle or Replace]
  E2 -- No --> T{Score band}
  T -- ≥68 --> RE[Repair]
  T -- 52–67 --> RU
  T -- 38–51 --> DO[Donate]
  T -- <38 --> RC[Recycle]
  DR & RP & RU & RR & RE & DO & RC --> R[Show result, explanation, next step]
  R --> L{Logged in?}
  L -- Yes --> SV[Save to history]
  L -- No --> X
  SV --> X([End])
```

## 6. ER diagram
```mermaid
erDiagram
  USERS ||--o{ ASSESSMENTS : makes
  USERS ||--o{ PASSWORD_RESET_TOKENS : requests
  USERS {
    int id PK
    text name
    text email UK
    text password_hash
    text role
    text created_at
  }
  ASSESSMENTS {
    int id PK
    int user_id FK
    text product_name
    text category
    int age
    text condition
    text functional_condition
    text cosmetic_condition
    text problem_type
    text repair_history
    text usage_frequency
    real repair_cost
    real replacement_cost
    text decision
    int score
    text confidence
    int quality
    text next_step
    text created_at
  }
  PASSWORD_RESET_TOKENS {
    int id PK
    int user_id FK
    text token UK
    text expires_at
    int used
    text created_at
  }
```

## 7. Deployment diagram
```mermaid
flowchart TB
  subgraph Client
    BR[Web browser]
  end
  subgraph GitHub
    REPO[(Repository)]
    CI[GitHub Actions: pytest]
  end
  subgraph Render
    PX[HTTPS proxy]
    subgraph WebService[Web service: Python 3.12]
      GU[gunicorn 2 workers x 4 threads]
      AP[Flask app]
      DBF[(SQLite file)]
    end
  end
  BR -->|HTTPS| PX --> GU --> AP --> DBF
  REPO --> CI
  REPO -->|auto-deploy on push| WebService
```
