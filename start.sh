#!/usr/bin/env bash
set -e

echo "╔══════════════════════════════════════════════╗"
echo "║      AI Database Copilot — Quick Start       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "❌ Python 3.11+ required. Install from https://python.org"
  exit 1
fi

# Check Node
if ! command -v node &>/dev/null; then
  echo "❌ Node.js 18+ required. Install from https://nodejs.org"
  exit 1
fi

# ─── Backend setup ────────────────────────────────────────────────────────────
echo "📦 Setting up backend..."
cd backend

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "⚠️  Created backend/.env — please add your GEMINI_API_KEY!"
fi

if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

pip install -q -r requirements.txt

echo "🌱 Seeding demo databases..."
python seed_demo_dbs.py

echo "🚀 Starting backend on http://localhost:8000"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

cd ..

# ─── Frontend setup ───────────────────────────────────────────────────────────
echo "📦 Setting up frontend..."
cd frontend

npm install -q

echo "🚀 Starting frontend on http://localhost:5173"
npm run dev &
FRONTEND_PID=$!

cd ..

echo ""
echo "✅ All services running!"
echo ""
echo "   Frontend : http://localhost:5173"
echo "   Backend  : http://localhost:8000"
echo "   API docs : http://localhost:8000/api/docs"
echo ""
echo "Press Ctrl+C to stop all services."
echo ""

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
