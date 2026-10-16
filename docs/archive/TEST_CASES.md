# ReWorth Test Cases — Professional Build

| ID | Scenario | Expected result |
|---|---|---|
| TC-01 | Good 2-year-old product, minor issue, low repair cost | Repair/Reuse depending on inputs; explanation shown |
| TC-02 | Costs left blank | No fake price; engine uses non-economic factors |
| TC-03 | Laptop does not work, exact fault unknown, no repair estimate | Diagnosis Required + Low confidence |
| TC-04 | Repair cost close to replacement | Recommendation reflects economic caution |
| TC-05 | Very old product with repeated repairs | Lower score; Recycle/Replace becomes more likely |
| TC-06 | Missing required assessment field | Clear validation message; no submission |
| TC-07 | Negative age/cost | API rejects the request |
| TC-08 | Logged-out assessment | Result works; assessment is not permanently stored |
| TC-09 | Logged-in assessment | Assessment is saved in dashboard history |
| TC-10 | Dashboard with no assessments | Friendly empty state and CTA |
| TC-11 | Existing older SQLite database | Startup migration adds new columns without requiring manual database recreation |
| TC-12 | Health endpoint | Returns app status and engine version |

## Viva demonstration cases

### Case A — Working but ageing phone
Show how age, condition, usage, repair history and cost together influence the result.

### Case B — Completely dead laptop
Select **Does not work**, use **Not sure** or a broad failure description, and leave repair cost unknown. ReWorth should avoid pretending to know the failed component and return **Diagnosis Required** when the information is insufficient.

### Case C — Known expensive repair
Provide repair and replacement estimates. Show the cost-comparison factor and explain how it changes the recommendation.
