# 🤖 AI Database Copilot

> An enterprise-grade, schema-aware conversational database assistant that converts natural language into optimized SQL — with security controls, risk analysis, query explanations, and a premium dark-mode UI.

---

## ✨ Features

| Feature | Details |
|---|---|
| **NL → SQL** | Ask in plain English, get production-ready SQL |
| **Multi-model AI** | Gemini Flash for simple queries, Pro for complex JOINs/mutations |
| **Schema-aware** | Reads your real schema — no hallucinated table names |
| **SQL Firewall** | Blocks DROP, TRUNCATE, injection, unguarded DELETE/UPDATE |
| **Confidence scores** | 0–100% with reasoning |
| **Risk analyzer** | Low / Medium / High / Critical with explanation |
| **Optimization engine** | Index suggestions, SELECT * warnings, JOIN analysis |
| **Query alternatives** | 2–3 ranked alternatives per query |
| **Clause explainer** | Beginner-friendly clause-by-clause breakdown |
| **Execution engine** | Run queries safely with row limits & timeouts |
| **Results table** | Sortable, paginated, up to 1000 rows |
| **Share links** | Shareable URLs for any generated query |
| **Audit log** | Tamper-evident hash-chain audit trail |
| **Analytics** | Usage charts, risk distribution, top tables |
| **History** | Search, filter, favorite, re-run past queries |
| **Demo databases** | E-commerce, University, HR — seed data included |
| **3 user modes** | Simple / Learning / Developer |
| **JWT auth** | Access + refresh tokens, bcrypt passwords |
| **RBAC** | Guest / User / Admin roles |
| **Dark UI** | Glassmorphism, animations, split-pane layout |

---

## 🚀 Quick Start (Local Dev)

### 1. Prerequisites

- Python 3.11+
- Node.js 18+
- A [Gemini API key](https://aistudio.google.com/)

### 2. Clone & start

```bash
git clone <repo>
cd ai-database-copilot
chmod +x start.sh
./start.sh
```

Then open: **http://localhost:5173**

### 3. Set your Gemini API key

Edit `backend/.env`:

```env
GEMINI_API_KEY=your-key-here
```

Restart the backend after editing.

---

## 🐳 Docker (Recommended)

```bash
cp backend/.env.example backend/.env
# Edit backend/.env and add GEMINI_API_KEY

docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs

---

## 📁 Project Structure

```
ai-database-copilot/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (auth, query, schema, analytics, history, ws)
│   │   ├── core/         # Config, DB, Security
│   │   ├── models/       # SQLAlchemy models (User, QueryHistory, Connection, AuditLog)
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # AI service, SQL firewall, DB connector, audit service
│   │   └── main.py
│   ├── demo_databases/   # Auto-seeded SQLite demo databases
│   ├── seed_demo_dbs.py  # Seeds ecommerce / university / HR databases
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/     # ConnectionSelector, NewConnectionModal
│   │   │   ├── sql/      # RightPanel, ResultsTable, SqlPanel
│   │   │   └── ui/       # Layout
│   │   ├── pages/        # ChatPage, LoginPage, RegisterPage, AnalyticsPage, HistoryPage, SharedQueryPage
│   │   ├── store/        # Zustand (auth + app state)
│   │   └── utils/        # axios API client
│   └── public/
│
├── docker-compose.yml
├── start.sh
└── README.md
```

---

## 🔒 Security Architecture

- **JWT** access + refresh tokens (configurable expiry)
- **bcrypt** password hashing (12 rounds)
- **SQL Firewall**: blocks DROP, TRUNCATE, ALTER, unguarded DELETE/UPDATE
- **Prompt injection detection**: regex-based pattern blocking
- **Read-only mode**: connections default to SELECT-only
- **Risk confirmation**: high/critical queries require explicit `confirm=true`
- **Tamper-evident audit log**: SHA-256 hash chain on every action
- **Rate limiting**: 30 req/min per IP (configurable)
- **RBAC**: Guest / User / Admin roles

---

## 🎓 User Modes

| Mode | Shows |
|---|---|
| **Simple** | Plain-language answer, query summary, results |
| **Learning** | SQL query + clause-by-clause explanation + learning tips |
| **Developer** | Full SQL + optimization score + performance metrics + alternatives |

---

## 🗄️ Supported Databases

| Database | Status |
|---|---|
| SQLite | ✅ Full support + demo databases |
| PostgreSQL | ✅ Full support |
| MySQL | ✅ Full support |
| SQL Server | 🔜 Architecture ready |
| Oracle | 🔜 Architecture ready |

---

## 🧪 Demo Databases

Connect instantly without your own database:

| Demo | Tables | Description |
|---|---|---|
| `ecommerce` | customers, products, orders, order_items | 50 customers, 100 orders, 200 items |
| `university` | students, departments, courses, professors, enrollments | 100 students, 20 courses |
| `hr` | employees, departments, attendance, performance_reviews | 60 employees, 500 attendance records |

---

## 🏗️ Tech Stack

**Backend**: FastAPI · SQLAlchemy · Pydantic · Python-Jose · Passlib · SQLparse · Slowapi  
**AI**: Google Gemini 2.0 Flash + 1.5 Pro (multi-model routing)  
**Frontend**: React 18 · Vite · Tailwind CSS · Zustand · React Query · Framer Motion · Recharts  
**Infra**: Docker · Nginx · Redis · SQLite/PostgreSQL/MySQL

---

## 📝 API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login → JWT tokens |
| GET | `/api/auth/me` | Get current user |
| GET | `/api/schema/connections` | List DB connections |
| POST | `/api/schema/connections` | Create connection |
| POST | `/api/schema/demo/{name}/connect` | Connect demo DB |
| POST | `/api/query/generate` | NL → SQL |
| POST | `/api/query/execute` | Execute query |
| GET | `/api/query/share/{token}` | Get shared query |
| GET | `/api/history/` | Query history |
| GET | `/api/analytics/dashboard` | Analytics data |
| WS | `/api/ws/progress/{session}` | Live progress |

Full interactive docs: http://localhost:8000/api/docs

---

## 🎯 Resume Positioning

> **AI Database Copilot** — A secure, schema-aware, enterprise-grade conversational database assistant that converts natural language into optimized SQL queries, explains query behavior in plain English, predicts execution impact, enforces multi-layer security controls, and serves both technical and non-technical users via an adaptive AI interface built with FastAPI, React, and Google Gemini.

**Key talking points:**
- Multi-model AI routing (Flash vs Pro based on query complexity)
- Tamper-evident audit log with SHA-256 hash chain
- SQL firewall with prompt injection detection
- Confidence scoring + query alternatives + clause explainer
- Three adaptive user modes (Simple / Learning / Developer)
- Real-time WebSocket query progress
- Sharable query links
- Three fully-seeded demo databases

---

## 📄 License

MIT — free to use, modify, and deploy.
