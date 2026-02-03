# Chatbot Architecture

**Role:** You are a Principal Full-Stack Architect.

**Objective:** Scaffold a **Multi-Tenant RAG Chatbot**.

**Tech Stack:**
* **Backend:** Python (FastAPI), SQLAlchemy (Async), PostgreSQL + pgvector.
* **Frontend:** React (Vite), Tailwind CSS, Framer Motion.
* **AI:** Google Gemini API (`google-generativeai`).

**Requirements:**

**1. Database Schema (Postgres)**
* `tenants`: id (UUID), name, api_key.
* `document_chunks`: id, tenant_id (FK), content, embedding (vector 768).
* **Critical:** All queries must filter by `tenant_id` for security.

**2. API Interface Contracts (Strict Implementation)**
Implement these exact Data Transfer Objects (DTOs):

* **POST /chat (Input):**
    ```json
    {
      "clientId": "uuid-string",
      "sessionId": "string",
      "message": "User question",
      "includeCitations": boolean
    }
    ```

* **POST /chat (Output):**
    ```json
    {
      "answer": "AI response string",
      "latencyMs": 850,
      "sources": [
        { "fileName": "policy.pdf", "snippet": "..." } // Only if includeCitations=true
      ]
    }
    ```

**3. Frontend (React)**
* **Design:** Apple-style aesthetics (Glassmorphism, `backdrop-blur`).
* **Animation:** Use Framer Motion for the chat window entry (slide up) and message bubbles.
* **Logic:**
    * Show "Suggested Chips" (e.g., "Pricing") when the chat is empty.
    * Include a toggle button in the UI settings for "Show Citations".

**Task:**
1.  Create the project structure (`backend/` and `frontend/`).
2.  Write `backend/main.py` implementing the DTOs above using Pydantic.
3.  Write `frontend/ChatWidget.jsx` with the Framer Motion animations.
