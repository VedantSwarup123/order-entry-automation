#!/bin/bash
# Starts the order entry demo: resets demo data, starts the backend (port 8000) and the dashboard (port 5173).
export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH
cd "$(dirname "$0")"

pkill -f "order-auto api" 2>/dev/null
pkill -f "vite --port 5173" 2>/dev/null

.venv/bin/python scripts/seed_demo_data.py
nohup .venv/bin/order-auto api > /tmp/demo-api.log 2>&1 &
(cd frontend && nohup npx vite --port 5173 > /tmp/demo-web.log 2>&1 &)

sleep 5
open http://localhost:5173/
echo "Demo running at http://localhost:5173  (stop it with: ./stop-demo.sh)"
