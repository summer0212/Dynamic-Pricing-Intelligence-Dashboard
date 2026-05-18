# Dynamic Pricing Intelligence Dashboard (MVP)

A full-stack, multi-tenant SaaS platform that uses Large Language Models to analyze inventory, margins, and market data to recommend optimized product prices. It features a "human-in-the-loop" approval workflow ensuring safe, reliable AI pricing adjustments.

## 🚀 Development Status: MVP (80% Complete)

This repository contains the core MVP. The fundamental architecture, database schemas, security models, and the AI intelligence engine are fully implemented and functional.

### What is Working Today:
*   ✅ **Authentication & Multi-Tenancy:** Secure JWT-based login/signup with role-based access control (Admin vs. Analyst) and strict organizational data isolation.
*   ✅ **AI Pricing Engine:** Integrated LangChain and Groq (`llama-3.1-8b-instant`). The engine uses strict Prompt Engineering and Pydantic Structured Outputs to guarantee the AI respects minimum margin thresholds and outputs mathematically sound pricing JSON.
*   ✅ **Graceful Fallbacks:** If the LLM provider fails, the system automatically falls back to a deterministic heuristic mathematical model to ensure 100% uptime.
*   ✅ **Approval Workflow:** Complete Human-in-the-Loop backend. When an admin approves an AI recommendation, the system atomically updates the product price and writes an immutable record to the Audit Log.
*   ✅ **Frontend Dashboards:** A Next.js/Tailwind dashboard displaying real-time product metrics and a dedicated Recommendations UI with review modals and status filtering.

### 🗺️ Next Steps & Roadmap (Remaining 20%):
*   **Products UI:** The backend API for full Product CRUD is complete, but the frontend UI for creating/editing products is pending (currently requires API testing tools).
*   **Audit Log UI:** The backend successfully generates Audit Logs upon price changes, but the frontend history table needs to be built.
*   **Temporal Orchestration:** The directory structure is scaffolded, but the Temporal workflows for scraping competitor data automatically on a schedule are pending.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | FastAPI (Python) | High-performance REST API |
| **Database** | PostgreSQL | Relational data storage |
| **ORM & Migrations**| SQLAlchemy 2.0 + Alembic | Object mapping and schema tracking |
| **AI/LLM** | LangChain + Groq | Orchestrating `llama-3.1-8b-instant` |
| **Frontend** | Next.js 16 + React 19 | Server/Client UI components |
| **Styling** | Tailwind CSS 4 | Utility-first responsive design |

---

## ⚙️ How to Run Locally

### 1. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create your virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the `backend/` directory with the following variables:
   ```env
   DATABASE_URL=postgresql://<user>:<password>@localhost:5432/pricing_dashboard
   JWT_SECRET_KEY=your_secure_secret_key
   JWT_ALGORITHM=HS256
   JWT_EXPIRATION_MINUTES=1440
   GROQ_API_KEY=your_groq_api_key
   ```
4. Run database migrations to set up the tables:
   ```bash
   alembic upgrade head
   ```
5. (Optional) Run the seed script to populate test data:
   ```bash
   python scripts/seed_data.py
   ```
6. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### 2. Frontend Setup
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```
4. Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🏗️ Architecture Overview

The application follows a strict layered architecture:
1.  **Frontend (`/frontend`)**: Handles user interactions, storing the JWT token in `localStorage` and calling the backend via a unified `api.ts` fetch wrapper.
2.  **API Routes (`/backend/app/routes`)**: Defines the REST endpoints and enforces Role-Based Access Control via Dependency Injection (`get_current_user`).
3.  **Schemas (`/backend/app/schemas`)**: Pydantic models validate all incoming and outgoing internet traffic.
4.  **Services (`/backend/app/services`)**: Houses complex business logic, specifically `pricing_engine.py` which formats the SQL data, queries Groq, and handles fallback logic.
5.  **Models (`/backend/app/models`)**: SQLAlchemy definitions dictating exactly how data looks inside PostgreSQL.
