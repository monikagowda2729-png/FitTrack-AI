# FitTrack AI 🏃

Internship Task 3 — Fitness Tracker App.

## Features
- Dashboard with steps, calories, workout time and streak
- Manual activity logging
- SQLite storage
- 7-day progress charts
- Activity history and deletion
- Gemini AI Coach for personalized, non-medical wellness suggestions
- Responsive Streamlit interface
- Render deployment configuration

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Set your Gemini API key before running:

PowerShell:
```powershell
$env:GEMINI_API_KEY="YOUR_KEY"
```

## Deploy on Render

Create a Render Web Service from this GitHub repository.
Build command:
`pip install -r requirements.txt`

Start command:
`streamlit run app.py --server.address 0.0.0.0 --server.port $PORT`

Add the environment variable:
`GEMINI_API_KEY`

Note: SQLite is ideal for a local/demo implementation. Render's free service filesystem is not intended as durable database storage. For production persistence, replace SQLite with Firebase/Firestore or a managed Postgres database.
