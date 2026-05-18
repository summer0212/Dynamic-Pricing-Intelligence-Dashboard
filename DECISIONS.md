# Architecture & Product Decisions (DECISIONS.md)

This document answers the core architectural, product, and technical questions regarding the development of the Klypup Dynamic Pricing Intelligence Dashboard.

## 1. Which option did you choose and why?
I built a **Dynamic Pricing Engine (Option A style core logic with human-in-the-loop workflows)**. I chose this because it demonstrates high business value and requires solving complex architectural challenges: multi-tenant data isolation, ACID compliance for pricing updates, and enforcing strict structural boundaries on LLM outputs to guarantee mathematically safe pricing recommendations.

## 2. Why this tech stack? What alternatives did you consider?
*   **Backend: FastAPI (Python)**
    *   *Why:* Python is the undisputed king of the AI/ML ecosystem, making integration with LangChain seamless. FastAPI provides asynchronous request handling, built-in Pydantic validation, and auto-generated OpenAPI docs (Swagger).
    *   *Alternatives:* Considered Django or Express.js. Django is too monolithic and heavy for an API-first approach, and Express (Node.js) lacks Python's native AI ecosystem libraries.
*   **Database: PostgreSQL + SQLAlchemy**
    *   *Why:* Pricing data requires strict ACID compliance and relational integrity (Orgs -> Users -> Products -> Recommendations). PostgreSQL handles this perfectly.
    *   *Alternatives:* MongoDB (NoSQL) was rejected because pricing and user data are inherently relational; lacking strict schemas could lead to fatal pricing errors.
*   **Frontend: Next.js + Tailwind CSS**
    *   *Why:* React/Next.js provides a robust component-based architecture for building interactive dashboards. Tailwind allows for rapid, premium UI styling without context-switching to CSS files.

## 3. How did you approach multi-tenancy? What pattern did you use and why?
I used the **Row-Level Tenant Isolation Pattern** (Logical Isolation).
*   *Implementation:* Every core table (`users`, `products`, `recommendations`) has an `org_id` foreign key. 
*   *Enforcement:* Multi-tenancy is enforced at the API layer via a FastAPI Dependency (`get_current_user`). Every protected route automatically injects the authenticated user. All SQLAlchemy queries explicitly append `.filter(Product.org_id == user.org_id)`.
*   *Why:* A separate database per tenant (Physical Isolation) is too expensive and complex to maintain for an MVP. Row-level isolation strikes the perfect balance of security and maintainability, provided it is strictly enforced via API dependencies.

## 4. How did you design the AI integration? What prompt engineering decisions did you make?
I avoided the standard RAG (Retrieval-Augmented Generation) approach. Because pricing data is structured (inventory count, cost, margins), semantic vector search is inappropriate.
Instead, I used an **Agentic Structured Output pattern**:
*   *Prompting:* The LLM (`llama-3.1-8b-instant` via Groq) is fed a strict System Prompt acting as a Senior Pricing Analyst. Product numbers and organizational margin floors are injected dynamically as context.
*   *Structured Output:* Using LangChain's `with_structured_output`, the LLM is forced to return a Pydantic schema (`PricingRecommendation`). This guarantees we get a parseable Float for the price, rather than unpredictable conversational text.
*   *Fallback Logic:* A `try/except` block wraps the LLM call. If the API fails or hallucinates, the system immediately drops to a deterministic mathematical heuristic (`_fallback_prediction`), ensuring 100% uptime.

## 5. What trade-offs did you make given the timeline?
*   **Frontend Product CRUD:** The backend API has full CRUD for products, but the frontend UI currently lacks the specific "Add/Edit Product" modal to save time, relying on seed scripts and Postman for generation.
*   **Temporal / Background Jobs:** AI generation happens synchronously in the request cycle. For 10,000 products, this would timeout. I scaffolded the `temporal/` directory, but did not implement the async worker pipelines to keep the MVP focused on the core workflow.

## 6. What would you improve with 2 more weeks?
1.  **Automated Daily Pipelines (Temporal):** Migrate the `generate_recommendation` logic to an async Temporal workflow that runs automatically at midnight, so analysts wake up to fresh recommendations.
2.  **Audit Log UI:** Build a historical tracking UI on the frontend to display the immutable audit logs created during the price approval process.
3.  **A/B Testing Module:** Allow the system to deploy the AI's recommended price to 50% of web traffic to statistically measure conversion rate impacts before globally applying it.

## 7. What was the hardest part and how did you solve it?
**The hardest part was ensuring the LLM didn't suggest prices that would lose the company money.** LLMs are notoriously bad at math and following strict numerical constraints. 
*   *Solution:* I solved this by implementing a **Multi-Layered Defense**:
    1. Instructing the LLM via prompt engineering to never go below the margin threshold.
    2. Using `with_structured_output` to force it to return a clean decimal.
    3. Writing a hardcoded Python validation step *after* the LLM returns its answer. If `llm_price < cost_price * margin_threshold`, the Python backend overrides the AI and floors the price at the absolute minimum acceptable margin.
