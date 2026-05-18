# Klypup Project — Complete Documentation

> **Dynamic Pricing Intelligence Dashboard**
> A full-stack, multi-tenant SaaS platform where an AI engine analyzes products and generates pricing recommendations, which admins review (approve/reject) through a human-in-the-loop workflow. On approval, the product price updates automatically and an audit trail is created.

---

## 1. Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Backend API** | FastAPI (Python) | ≥ 0.104 |
| **Database** | PostgreSQL | — |
| **ORM** | SQLAlchemy 2.0 (Declarative) | ≥ 2.0 |
| **Migrations** | Alembic | ≥ 1.12 |
| **Auth** | JWT (python-jose) + bcrypt (passlib) | — |
| **Config** | pydantic-settings (.env) | ≥ 2.0 |
| **Frontend** | Next.js 16 (App Router) | 16.2.6 |
| **UI** | React 19 + TailwindCSS 4 | — |
| **AI (planned)** | LangChain + Groq | In requirements, mock for now |
| **Orchestration (planned)** | Temporal | Scaffolded, not implemented |

---

## 2. High-Level System Architecture

```mermaid
graph LR
    subgraph Client["Browser (localhost:3000)"]
        NextJS["Next.js 16<br/>App Router + TailwindCSS 4"]
    end

    subgraph Server["Backend (localhost:8000)"]
        FastAPI["FastAPI<br/>REST API"]
        Engine["Mock Pricing Engine<br/>(will become AI Agent)"]
    end

    subgraph Database["PostgreSQL"]
        PG["pricing_dashboard<br/>7 tables"]
    end

    NextJS -- "HTTP REST<br/>+ JWT Bearer Token" --> FastAPI
    FastAPI -- "SQLAlchemy ORM" --> PG
    FastAPI --> Engine
    Engine -- "reads product data" --> PG
```

---

## 3. What Has Been Built — Feature Map

### Feature 1: Authentication & Multi-Tenancy

- **Signup** — Create a new user + organization (admin) or join existing org via invite code (analyst)
- **Login** — Email + password → JWT token
- **JWT middleware** — Every protected route extracts user from Bearer token
- **Role-based access** — `admin` can write (create/update/delete products, generate & review recommendations); `analyst` can only read
- **Multi-tenant isolation** — All queries filter by `user.org_id` so each organization sees only its own data

### Feature 2: Product Management (CRUD)

- **List products** — All products for the user's organization
- **Create product** — Admin only (name, SKU, category, price, cost, inventory, margin threshold)
- **Get single product** — By ID (org-scoped)
- **Update product** — Admin only, partial updates
- **Delete product** — Admin only

### Feature 3: AI Price Recommendations + Human-in-the-Loop Approval

- **Generate predictions** — Triggers the mock pricing engine for all products (or a single one). Creates `pending` recommendations
- **List recommendations** — With optional status filter (`?status=pending|approved|rejected`)
- **Review modal** — Shows price comparison, % change, confidence score, AI rationale, and agent analysis JSON
- **Approve** — Updates product price to recommended price, creates audit log entry, marks recommendation as approved
- **Reject** — Marks recommendation as rejected with review note

### Supporting Infrastructure

- **Seed data** — 2 orgs (TechCorp, RetailHub), 3 users, 11 products pre-loaded
- **Alembic migration** — Single migration creating all 7 tables
- **Health check** — `GET /health` → `{"status": "Ok"}`

---

## 4. Complete Application Flow

```mermaid
flowchart TD
    A["User visits /login"] --> B{"Login or Signup?"}

    B -->|Login| C["POST /api/auth/login<br/>email + password"]
    B -->|Signup| D["POST /api/auth/signup<br/>email + password + name + org_name or invite_code"]

    C --> E["Backend verifies password with bcrypt<br/>Generates JWT token"]
    D --> F["Backend creates Org + User<br/>Generates JWT token"]

    E --> G["TokenResponse<br/>access_token, user_id, role, org_name"]
    F --> G

    G --> H["Frontend stores in localStorage<br/>Redirects to /dashboard"]

    H --> I["Dashboard loads"]
    I --> J["Parallel API calls:<br/>GET /api/products<br/>GET /api/recommendations?status=pending"]
    J --> K["Renders 5 summary cards<br/>+ Recent Products table"]

    K --> L{"User navigates to?"}
    L -->|Recommendations| M["GET /api/recommendations"]
    M --> N["Renders recommendation table<br/>with status filter tabs"]

    N --> O{"Admin clicks?"}
    O -->|Generate Predictions| P["POST /api/recommendations/generate"]
    P --> Q["Mock engine analyzes each product<br/>Creates pending recommendations"]
    Q --> N

    O -->|Review| R["Opens review modal<br/>Shows price comparison + rationale"]
    R --> S{"Approve or Reject?"}

    S -->|Approve| T["PUT /api/recommendations/id/review<br/>status: approved, review_note"]
    T --> U["Backend in single transaction:<br/>1. product.current_price = recommended_price<br/>2. Create AuditLog entry<br/>3. recommendation.status = approved"]
    U --> N

    S -->|Reject| V["PUT /api/recommendations/id/review<br/>status: rejected, review_note"]
    V --> W["recommendation.status = rejected"]
    W --> N

    L -->|Logout| X["localStorage.clear<br/>Redirect to /login"]
```

---

## 5. Auth Flow — Sequence Diagram

```mermaid
sequenceDiagram
    participant Browser
    participant Frontend as Next.js
    participant API as FastAPI
    participant DB as PostgreSQL

    Note over Browser,DB: SIGNUP - new organization
    Browser->>Frontend: Fill form with email, password, name, org_name
    Frontend->>API: POST /api/auth/signup
    API->>DB: Check email uniqueness
    API->>DB: INSERT Organization + OrgSettings
    API->>DB: INSERT User with role=admin and bcrypt hash
    API->>API: jwt.encode with user_id, org_id, exp
    API-->>Frontend: access_token, user_id, role, org_name
    Frontend->>Frontend: localStorage.setItem for token, role, etc
    Frontend->>Browser: router.push to /dashboard

    Note over Browser,DB: SIGNUP - join existing org
    Browser->>Frontend: Fill form with email, password, name, invite_code
    Frontend->>API: POST /api/auth/signup
    API->>DB: Find org by invite_code
    API->>DB: INSERT User with role=analyst
    API-->>Frontend: TokenResponse

    Note over Browser,DB: LOGIN
    Browser->>Frontend: Fill form with email and password
    Frontend->>API: POST /api/auth/login
    API->>DB: Query User by email
    API->>API: bcrypt.verify password against hash
    API->>API: jwt.encode with user_id, org_id, exp
    API-->>Frontend: TokenResponse

    Note over Browser,DB: AUTHENTICATED REQUEST
    Frontend->>API: GET /api/products with Authorization Bearer token
    API->>API: jwt.decode token to get user_id, org_id
    API->>DB: Query User by user_id
    API->>DB: Query Products WHERE org_id = user.org_id
    API-->>Frontend: ProductResponse list
```

---

## 6. Recommendation + Approval Flow — Sequence Diagram

```mermaid
sequenceDiagram
    participant Admin as Admin Browser
    participant FE as Frontend
    participant API as FastAPI
    participant Engine as Mock Pricing Engine
    participant DB as PostgreSQL

    Note over Admin,DB: GENERATE PREDICTIONS
    Admin->>FE: Clicks Generate Predictions
    FE->>API: POST /api/recommendations/generate
    API->>API: Verify role is admin
    API->>DB: Query all Products where org_id matches
    loop For each product
        API->>Engine: generate_mock_prediction with product
        Engine->>Engine: Analyze inventory, cost, margin
        Engine-->>API: recommended_price, confidence_score, rationale, agent_outputs
        API->>DB: INSERT Recommendation with status=pending
    end
    API-->>FE: List of RecommendationResponse
    FE->>Admin: Table shows new pending recommendations

    Note over Admin,DB: APPROVE A RECOMMENDATION
    Admin->>FE: Clicks Review then Approve
    FE->>API: PUT /api/recommendations/id/review with approved
    API->>API: Verify role is admin and rec status is pending
    API->>DB: UPDATE product SET current_price = recommended_price
    API->>DB: INSERT AuditLog with action=price_approved
    API->>DB: UPDATE recommendation SET status=approved
    API->>DB: COMMIT single transaction
    API-->>FE: Updated RecommendationResponse
    FE->>Admin: Table refreshes with approved status

    Note over Admin,DB: REJECT A RECOMMENDATION
    Admin->>FE: Clicks Reject
    FE->>API: PUT /api/recommendations/id/review with rejected
    API->>DB: UPDATE recommendation SET status=rejected with review_note
    API-->>FE: Updated RecommendationResponse
```

---

## 7. Backend — Component-Level Architecture

```mermaid
graph TB
    subgraph Entry["Entry Point"]
        Main["main.py<br/>FastAPI app + CORS + 3 routers + /health"]
    end

    subgraph Routes["Routes Layer - API Endpoints"]
        AuthRoutes["routes/auth.py<br/>POST /api/auth/signup<br/>POST /api/auth/login"]
        ProductRoutes["routes/products.py<br/>GET POST /api/products<br/>GET PUT DELETE /api/products/id"]
        RecRoutes["routes/recommendations.py<br/>POST /api/recommendations/generate<br/>GET /api/recommendations<br/>GET /api/recommendations/id<br/>PUT /api/recommendations/id/review"]
    end

    subgraph Middleware["Auth Middleware"]
        AuthMW["middleware/auth_middleware.py<br/>get_current_user dependency<br/>Extracts user from Bearer JWT"]
    end

    subgraph Services["Business Logic"]
        PricingEngine["services/pricing_engine.py<br/>generate_mock_prediction<br/>Replace with real AI agent"]
    end

    subgraph Schemas["Validation with Pydantic"]
        AuthSchemas["schemas/auth.py<br/>SignupRequest, LoginRequest, TokenResponse"]
        ProductSchemas["schemas/product.py<br/>ProductCreate, ProductUpdate, ProductResponse"]
        RecSchemas["schemas/recommendation.py<br/>PredictionRequest, RecommendationReview, RecommendationResponse"]
    end

    subgraph Models["ORM Models with SQLAlchemy"]
        OrgModel["Organization"]
        UserModel["User with admin or analyst role"]
        ProductModel["Product"]
        RecModel["Recommendation with pending, approved, rejected, auto_executed"]
        CompModel["CompetitorPrice"]
        AuditModel["AuditLog"]
        SettingsModel["OrgSettings"]
    end

    subgraph Utils["Security Utilities"]
        Security["utils/security.py<br/>hash_password, verify_password<br/>create_access_token, decode_access_token"]
    end

    subgraph DB["Database Layer"]
        Config["config.py<br/>pydantic-settings from .env"]
        Database["database.py<br/>Engine + SessionLocal + get_db"]
    end

    Main --> AuthRoutes
    Main --> ProductRoutes
    Main --> RecRoutes

    ProductRoutes --> AuthMW
    RecRoutes --> AuthMW
    AuthMW --> Security
    AuthRoutes --> Security

    RecRoutes --> PricingEngine

    AuthRoutes --> AuthSchemas
    ProductRoutes --> ProductSchemas
    RecRoutes --> RecSchemas

    AuthRoutes --> OrgModel
    AuthRoutes --> UserModel
    AuthRoutes --> SettingsModel
    ProductRoutes --> ProductModel
    RecRoutes --> RecModel
    RecRoutes --> ProductModel
    RecRoutes --> AuditModel

    Models --> Database
    Database --> Config
```

---

## 8. Frontend — Component-Level Architecture

```mermaid
graph TB
    subgraph Layout["Root Layout"]
        RootLayout["layout.tsx<br/>HTML shell + Geist fonts + globals.css"]
    end

    subgraph Pages["Pages via App Router"]
        Landing["page.tsx at /<br/>Default Next.js template - not customized"]
        LoginPage["login/page.tsx at /login<br/>Login and Signup form<br/>Toggles between login/signup mode<br/>Stores token in localStorage"]
        DashboardPage["dashboard/page.tsx at /dashboard<br/>5 summary cards<br/>Recent Products table<br/>Fetches products + pending count"]
        RecsPage["recommendations/page.tsx at /recommendations<br/>Filter tabs for All, Pending, Approved, Rejected<br/>Recommendations table<br/>Review and Detail modal"]
    end

    subgraph APILayer["API Client"]
        ApiTS["lib/api.ts<br/>apiCall Fetch wrapper with auto Bearer token<br/>Auth: signup, login<br/>Products: getProducts, createProduct, deleteProduct<br/>Recs: getRecommendations, generateRecommendations, reviewRecommendation"]
    end

    subgraph State["Client-Side State"]
        LS["localStorage<br/>token, role, org_name, user_id"]
    end

    RootLayout --> Landing
    RootLayout --> LoginPage
    RootLayout --> DashboardPage
    RootLayout --> RecsPage

    LoginPage --> ApiTS
    DashboardPage --> ApiTS
    RecsPage --> ApiTS

    ApiTS --> LS
    LoginPage --> LS
    DashboardPage --> LS
    RecsPage --> LS

    ApiTS -- "HTTP + Bearer Token" --> Backend["FastAPI at port 8000"]
```

---

## 9. Database Schema — ER Diagram

```mermaid
erDiagram
    organizations ||--o{ users : "has many"
    organizations ||--o{ products : "has many"
    organizations ||--o{ recommendations : "has many"
    organizations ||--o{ audit_log : "has many"
    organizations ||--|| org_settings : "has one"
    products ||--o{ competitor_prices : "has many"
    products ||--o{ recommendations : "has many"
    products ||--o{ audit_log : "has many"
    users ||--o{ recommendations : "reviewed_by"
    users ||--o{ audit_log : "performed_by"
    recommendations ||--o{ audit_log : "references"

    organizations {
        UUID id PK
        String name
        String invite_code UK
        DateTime created_at
    }

    users {
        UUID id PK
        String email
        String password_hash
        String name
        UUID org_id FK
        Enum role "admin or analyst"
        DateTime created_at
    }

    products {
        UUID id PK
        UUID org_id FK
        String name
        String sku
        String category
        Numeric current_price
        Numeric cost_price
        Integer inventory_count
        Numeric margin_threshold
        DateTime created_at
        DateTime updated_at
    }

    recommendations {
        UUID id PK
        UUID org_id FK
        UUID product_id FK
        Numeric recommended_price
        Numeric current_price "snapshot at generation time"
        Numeric confidence_score
        Enum status "pending or approved or rejected or auto_executed"
        Text rationale
        JSONB agent_outputs
        UUID reviewed_by FK
        Text review_note
        DateTime created_at
    }

    competitor_prices {
        UUID id PK
        UUID product_id FK
        String competitor_name
        Numeric price
        DateTime scraped_at
    }

    audit_log {
        UUID id PK
        UUID org_id FK
        UUID product_id FK
        UUID recommendation_id FK
        String action
        Numeric old_price
        Numeric new_price
        UUID performed_by FK
        Text reason
        DateTime created_at
    }

    org_settings {
        UUID id PK
        UUID org_id FK
        Numeric auto_execute_threshold "default 0.85"
        JSONB margin_floors "category-specific floors"
        DateTime created_at
        DateTime updated_at
    }
```

---

## 10. API Endpoints — Complete Reference

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| `GET` | `/health` | No | — | Health check |
| `POST` | `/api/auth/signup` | No | — | Register user + create/join org |
| `POST` | `/api/auth/login` | No | — | Login and get JWT token |
| `GET` | `/api/products/` | Yes | All | List org products |
| `POST` | `/api/products/` | Yes | Admin | Create product |
| `GET` | `/api/products/{id}` | Yes | All | Get single product |
| `PUT` | `/api/products/{id}` | Yes | Admin | Update product partially |
| `DELETE` | `/api/products/{id}` | Yes | Admin | Delete product |
| `POST` | `/api/recommendations/generate` | Yes | Admin | Generate mock AI predictions |
| `GET` | `/api/recommendations/` | Yes | All | List recommendations with optional status filter |
| `GET` | `/api/recommendations/{id}` | Yes | All | Get single recommendation |
| `PUT` | `/api/recommendations/{id}/review` | Yes | Admin | Approve or reject a recommendation |

---

## 11. Directory Structure

```
Klypup_project/
├── backend/
│   ├── .env                          # DATABASE_URL, JWT_SECRET, GROQ_API_KEY
│   ├── requirements.txt              # Python dependencies
│   ├── alembic.ini                   # Alembic config
│   ├── alembic/
│   │   ├── env.py                    # Imports all models for autogenerate
│   │   └── versions/
│   │       └── 17613b87962d_create_all_tables.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app + CORS + 3 routers
│   │   ├── config.py                 # Settings from .env via pydantic-settings
│   │   ├── database.py               # SQLAlchemy engine + session + get_db
│   │   ├── models/
│   │   │   ├── organization.py       # Organization with id, name, invite_code
│   │   │   ├── user.py               # User with email, password_hash, role, org_id
│   │   │   ├── product.py            # Product with name, sku, category, prices, inventory
│   │   │   ├── recommendation.py     # Recommendation with recommended_price, confidence, status
│   │   │   ├── competitor_price.py   # CompetitorPrice with competitor_name, price
│   │   │   ├── audit_log.py          # AuditLog with action, old_price, new_price
│   │   │   └── org_settings.py       # OrgSettings with auto_execute_threshold, margin_floors
│   │   ├── schemas/
│   │   │   ├── auth.py               # SignupRequest, LoginRequest, TokenResponse
│   │   │   ├── product.py            # ProductCreate, ProductUpdate, ProductResponse
│   │   │   └── recommendation.py     # PredictionRequest, RecommendationReview, RecommendationResponse
│   │   ├── routes/
│   │   │   ├── auth.py               # POST /signup, /login
│   │   │   ├── products.py           # CRUD /api/products
│   │   │   └── recommendations.py    # /generate, list, get, /review
│   │   ├── services/
│   │   │   └── pricing_engine.py     # Mock engine - swap for real AI agent
│   │   ├── middleware/
│   │   │   └── auth_middleware.py     # get_current_user JWT dependency
│   │   └── utils/
│   │       └── security.py           # hash, verify, JWT encode/decode
│   ├── scripts/
│   │   ├── seed_data.py              # Seeds 2 orgs, 3 users, 11 products
│   │   └── verify_approval.py        # DB verification script
│   └── temporal/                     # Scaffolded only, directories are empty
│       ├── activities/
│       └── workflows/
│
└── frontend/
    ├── package.json                  # Next.js 16, React 19, TailwindCSS 4
    ├── next.config.ts
    ├── tsconfig.json
    └── src/
        ├── lib/
        │   └── api.ts                # Fetch wrapper + 8 API functions
        └── app/
            ├── layout.tsx            # Root layout with Geist fonts
            ├── globals.css           # Tailwind + theme variables
            ├── page.tsx              # Landing page, default Next.js template
            ├── login/
            │   └── page.tsx          # Login and Signup form
            ├── dashboard/
            │   └── page.tsx          # 5 summary cards + products table
            └── recommendations/
                └── page.tsx          # Filter tabs + recommendations table + review modal
```

---

## 12. AI Orchestration Flow

The core intelligence is powered by LangChain and Groq (`llama-3.1-8b-instant`), utilizing Structured Output to guarantee safe, parseable responses.

```mermaid
flowchart TD
    A["API Request<br/>POST /generate"] --> B["Fetch Product & Org Settings<br/>from PostgreSQL"]
    B --> C["LangChain Orchestrator<br/>(pricing_engine.py)"]
    
    C --> D{"Try LLM Call"}
    
    D -->|Success| E["Groq LPU<br/>llama-3.1-8b-instant"]
    E --> F["System Prompt<br/>(Role: Pricing Analyst)"]
    F --> G["with_structured_output<br/>(Pydantic Schema)"]
    G --> H["Python Validation<br/>(Floor price against margin)"]
    
    D -->|Failure/Timeout| I["Graceful Fallback<br/>(Heuristic Math Model)"]
    
    H --> J["Structured Output<br/>price, rationale, confidence"]
    I --> J
    
    J --> K["Save to Database<br/>(Status: Pending)"]
```

---

## 13. Seed Data — Pre-loaded

| Organization | Invite Code | Admin User | Analyst User | Products |
|---|---|---|---|---|
| **TechCorp** | `TECH2026` | admin@techcorp.com / admin123 | analyst@techcorp.com / analyst123 | 8 products |
| **RetailHub** | `RETAIL26` | admin@retailhub.com / admin123 | — | 3 products |

### TechCorp Products

| Product | SKU | Category | Price | Cost | Stock |
|---|---|---|---|---|---|
| Sony WH-1000XM5 | SONY-WH1000 | electronics | 24,990 | 18,000 | 150 |
| Samsung Galaxy S24 | SAM-S24 | electronics | 79,999 | 55,000 | 80 |
| Nike Air Max 90 | NIKE-AM90 | apparel | 12,995 | 7,000 | 200 |
| Dyson V15 Detect | DYS-V15 | home_goods | 52,990 | 35,000 | 45 |
| Apple AirPods Pro | APL-APP2 | electronics | 24,900 | 17,000 | 120 |
| Levi's 501 Jeans | LEV-501 | apparel | 4,999 | 2,500 | 300 |
| Instant Pot Duo | IP-DUO | home_goods | 8,999 | 5,500 | 90 |
| JBL Flip 6 | JBL-FL6 | electronics | 9,999 | 6,000 | 175 |

---

## 14. Multi-Tenant Data Flow

Data isolation is strictly enforced at the Application level (Row-level multi-tenancy) so no tenant can ever see another's data.

```mermaid
sequenceDiagram
    participant User
    participant Middleware as Auth Middleware
    participant API as FastAPI Route
    participant DB as PostgreSQL
    
    User->>Middleware: GET /products + JWT Token
    Middleware->>Middleware: Decode JWT to get org_id
    Middleware->>API: Inject User object
    API->>DB: SELECT * FROM products WHERE org_id = user.org_id
    DB-->>API: Filtered Data
    API-->>User: Secure JSON Response
```

---

## 15. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **JWT in localStorage** | Simple client-side auth for a dashboard app. Tokens expire after 24 hours. |
| **org_id on every query** | Multi-tenant data isolation — users can never access another org's data. |
| **Recommendation stores current_price snapshot** | Captures the price at the time of generation, so the comparison remains valid even if the product price changes later. |
| **Single-transaction approval** | Product price update + audit log + recommendation status change all commit atomically — no partial state. |
| **Mock engine is a separate service file** | Clean separation — swap pricing_engine.py for the real AI agent without touching routes or schemas. |
| **Admin-only writes, analyst read-only** | Role-based access: admins manage products and approve recommendations; analysts view dashboards and recommendations. |
| **Pydantic v2 schemas with from_attributes** | Enables ORM mode for seamless SQLAlchemy to Pydantic serialization. |
