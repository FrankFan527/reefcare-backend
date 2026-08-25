# ReefCare MY Backend

Backend API for **ReefCare MY**, built with **FastAPI**.

ReefCare MY is an AI-assisted, privacy-aware reef observation and conservation coordination platform. It helps reef observers submit useful reef-threat observations and enables authorised Case Coordinators to review reports, make traceable decisions, and provide status updates back to observers.

## Tech Stack

* Python 3.12
* FastAPI
* Uvicorn
* Pydantic
* Git / GitHub

Additional database, authentication, AI, and external integration dependencies will be added as development progresses.

## Project Structure

```text
reefcare-backend/
│
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   └── __init__.py
│   │   └── __init__.py
│   │
│   ├── core/
│   │   └── __init__.py
│   │
│   ├── db/
│   │   └── __init__.py
│   │
│   ├── models/
│   │   └── __init__.py
│   │
│   ├── schemas/
│   │   └── __init__.py
│   │
│   ├── services/
│   │   └── __init__.py
│   │
│   ├── __init__.py
│   └── main.py
│
├── tests/
│   └── __init__.py
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

### Folder Responsibilities

* `app/api/routes/` — API endpoints and route definitions
* `app/core/` — application configuration, security, and shared settings
* `app/db/` — database connection and database session setup
* `app/models/` — database models
* `app/schemas/` — Pydantic request and response schemas
* `app/services/` — business logic
* `tests/` — backend tests
* `app/main.py` — FastAPI application entry point

## Current API

The current backend includes basic application and health-check endpoints.

### Root

```http
GET /
```

Example response:

```json
{
  "message": "ReefCare MY backend is running"
}
```

### Health Check

```http
GET /health
```

Example response:

```json
{
  "status": "ok"
}
```

## Local Setup

### 1. Clone the Repository

```bash
git clone https://github.com/FrankFan527/reefcare-backend.git
cd reefcare-backend
```

### 2. Create a Virtual Environment

Windows:

```bash
py -3.12 -m venv venv
```

### 3. Activate the Virtual Environment

PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

After activation, the terminal should display:

```text
(venv)
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Environment Variables

Copy `.env.example` to a local `.env` file when environment-specific configuration is required.

Example:

```text
APP_NAME=ReefCare MY
APP_ENV=development
```

Do not commit `.env` files containing credentials or secrets.

## Running the Backend

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

The server should run at:

```text
http://127.0.0.1:8000
```

## API Documentation

FastAPI automatically provides interactive API documentation.

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

Alternative API documentation:

```text
http://127.0.0.1:8000/redoc
```

## Iteration 1 Backend Scope

The initial backend will support the minimum ReefCare closed-loop workflow:

```text
Observer
   ↓
Create / Select Dive Session
   ↓
Submit Observation Report
   ↓
Initial Intake
   ↓
Case Coordinator Claims Report
   ↓
Review and Decision
   ↓
Status History
   ↓
Observer Tracks Outcome
```

Initial backend development will focus on:

* user roles and basic access control
* observer accounts
* dive sessions
* reef observation reports
* evidence records
* privacy-aware location data
* Case Coordinator ownership
* report review and decisions
* report status history
* observer report tracking

AI assistance, advanced triage, conservation action monitoring, and external environmental integrations will be added in later development stages where required.

## Development Principle

ReefCare follows the principle:

**AI assists. Humans verify and decide.**

The core workflow should continue to function even when AI functionality is unavailable.

## Git Workflow

Before starting work:

```bash
git pull
```

Create a separate development branch where appropriate:

```bash
git checkout -b feature/your-feature-name
```

After completing and testing changes:

```bash
git add .
git commit -m "Describe the completed change"
git push
```

Do not commit:

* `venv/`
* `__pycache__/`
* `.env`
* local IDE configuration
* credentials or API keys
