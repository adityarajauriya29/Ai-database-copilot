# 🤖 AI Database Copilot

> **AI Database Copilot** is an enterprise-grade, schema-aware conversational database assistant that converts natural language into optimized SQL queries using **Google Gemini AI**, while providing security controls, risk analysis, query explanations, execution insights, and an elegant enterprise UI.

<p align="center">

![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)
![Google Gemini](https://img.shields.io/badge/Google-Gemini_AI-4285F4?logo=google)
![JWT](https://img.shields.io/badge/Auth-JWT-orange)
![License](https://img.shields.io/badge/License-MIT-green)

</p>

---

# 🌐 Live Deployment

## 🚀 Frontend (Vercel)

**https://ai-database-copilot-five.vercel.app**

## ⚡ Backend API (Render)

**https://ai-database-copilot-aw7z.onrender.com**

## 📖 API Documentation

**https://ai-database-copilot-aw7z.onrender.com/api/docs**

---

# ✨ Features

| Feature | Details |
|---|---|
| **Natural Language → SQL** | Convert plain English into optimized SQL |
| **Multi-Model AI** | Gemini Flash for simple queries, Gemini Pro for complex SQL |
| **Schema Aware** | Generates queries using actual database schema |
| **SQL Firewall** | Prevents SQL Injection, DROP, TRUNCATE, ALTER, unsafe DELETE/UPDATE |
| **Confidence Score** | AI confidence for every generated query |
| **Risk Analyzer** | Low / Medium / High / Critical query analysis |
| **Optimization Engine** | Index suggestions, JOIN analysis, optimization hints |
| **Clause Explainer** | Beginner-friendly explanation of SQL clauses |
| **Alternative Queries** | Multiple optimized query suggestions |
| **Execution Engine** | Secure execution with row limits & timeout |
| **Results Viewer** | Sortable, paginated SQL result tables |
| **Analytics Dashboard** | Query statistics and risk visualization |
| **Query History** | Save, search, rerun and favorite previous queries |
| **Audit Logging** | Tamper-evident SHA-256 audit trail |
| **JWT Authentication** | Secure authentication with refresh tokens |
| **Role-Based Access** | Guest, User and Admin roles |
| **Responsive UI** | Enterprise-grade glassmorphism interface |
| **Demo Databases** | University, HR and Ecommerce sample databases |

---

# 📸 Application Screenshots

> Add screenshots inside a **docs/** folder.

## Login

![Login](docs/login.png)

---

## Chat Interface

![Chat](docs/chat.png)

---

## Analytics Dashboard

![Analytics](docs/analytics.png)

---

## Query History

![History](docs/history.png)

---

# 🏗️ System Architecture

```text
                  User
                    │
                    ▼
          React + Vite Frontend
                    │
                    ▼
        FastAPI REST API Backend
                    │
     ┌──────────────┼──────────────┐
     ▼              ▼              ▼
 Google Gemini   SQL Firewall   Analytics
       │              │              │
       └──────────────┼──────────────┘
                      │
                      ▼
      SQLite / PostgreSQL / MySQL
```

---

# 🚀 Quick Start

## Prerequisites

- Python 3.11+
- Node.js 18+
- Google Gemini API Key

---

## Clone Repository

```bash
git clone https://github.com/adityarajauriya29/Ai-database-copilot.git

cd Ai-database-copilot
```

---

## Backend

```bash
cd backend

python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --reload
```

---

## Frontend

```bash
cd frontend

npm install

npm run dev
```

---

Frontend:

```
http://localhost:5173
```

Backend:

```
http://localhost:8000
```

API Docs:

```
http://localhost:8000/api/docs
```

---

# 🐳 Docker Deployment

```bash
cp backend/.env.example backend/.env

# Add your Gemini API Key

docker-compose up --build
```

---

# 📂 Project Structure

```
Ai-database-copilot/

│

├── backend/

│   ├── app/

│   │   ├── api/

│   │   ├── core/

│   │   ├── models/

│   │   ├── schemas/

│   │   ├── services/

│   │   └── main.py

│   ├── demo_databases/

│   ├── requirements.txt

│   └── .env.example

│

├── frontend/

│   ├── src/

│   ├── public/

│   ├── package.json

│   └── vite.config.js

│

├── docker-compose.yml

├── README.md

└── docs/
```

---

# 🔒 Security Features

- JWT Authentication
- Refresh Tokens
- Password Hashing (bcrypt)
- SQL Firewall
- Prompt Injection Detection
- Read-only Database Mode
- Query Risk Classification
- Rate Limiting
- SHA-256 Audit Chain
- Role-Based Access Control

---

# 🎓 User Modes

| Mode | Description |
|------|-------------|
| Simple | Easy-to-understand AI responses |
| Learning | SQL explanation with learning tips |
| Developer | Full SQL, optimization metrics and alternatives |

---

# 🗄️ Supported Databases

| Database | Support |
|----------|---------|
| SQLite | ✅ |
| PostgreSQL | ✅ |
| MySQL | ✅ |
| SQL Server | 🔜 |
| Oracle | 🔜 |

---

# 🧪 Demo Databases

| Database | Description |
|-----------|-------------|
| University | Students, Courses, Professors |
| HR | Employees, Attendance, Performance |
| Ecommerce | Customers, Products, Orders |

---

# 🏗️ Tech Stack

### Frontend

- React 18
- Vite
- Tailwind CSS
- Zustand
- React Query
- Framer Motion
- Recharts

### Backend

- FastAPI
- SQLAlchemy
- Pydantic
- Python-Jose
- Passlib
- SlowAPI
- SQLParse

### AI

- Google Gemini Flash
- Google Gemini Pro

### Databases

- SQLite
- PostgreSQL
- MySQL

### Deployment

- Vercel
- Render
- Docker

---

# 📡 API Endpoints

| Method | Endpoint |
|---------|----------|
| POST | `/api/auth/register` |
| POST | `/api/auth/login` |
| GET | `/api/auth/me` |
| POST | `/api/query/generate` |
| POST | `/api/query/execute` |
| GET | `/api/query/share/{token}` |
| GET | `/api/history` |
| GET | `/api/analytics/dashboard` |

---

# 💼 Resume Highlights

- AI-powered SQL generation using Google Gemini
- Multi-model AI routing
- SQL Firewall with Prompt Injection Detection
- Enterprise-grade Authentication
- Risk Prediction & Query Optimization
- Analytics Dashboard
- Real-time Query Execution
- Multi-Database Support
- Modern Responsive UI

---

# 🔮 Future Enhancements

- SQL Server Support
- Oracle Support
- AI Query Auto Correction
- Voice-to-SQL
- Database ER Diagram Generator
- Team Collaboration
- Saved AI Prompts
- Explain Execution Plans

---

# 👨‍💻 Developer

**Aditya Rajauriya**

B.Tech Computer Science Engineering

AI • Machine Learning • Full Stack Development

GitHub

https://github.com/adityarajauriya29

LinkedIn

(Add your LinkedIn URL)

---

# 📄 License

MIT License

Copyright (c) 2026 Aditya Rajauriya

Feel free to use, modify and distribute this project.