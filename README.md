# WILD WITHIN — Habit Lab dashboard

A responsive Flask prototype for personal routines, daily check-ins, small habit experiments, a motivational virtual journey, and a local community demo feed.

## Run on Windows
1. Install Python 3.11+ (Python 3.12 is a good compatibility default).
2. Open PowerShell in this folder.
3. Run:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe app.py
   ```
4. Visit http://127.0.0.1:5055

## Deploy on Render
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Set `DATABASE_PATH` to a file path on a persistent disk if you want SQLite data to survive service restarts/redeploys. Without persistent storage, free ephemeral instances may lose saved data.
- Render can deploy from the connected GitHub repository. Push commits to trigger a new deploy.

## What works in this prototype
- Responsive forest-inspired dashboard and dark appearance toggle.
- Add daily rituals and mark/unmark completion for today.
- Habit Lab: create a 3–90 day experiment with hypothesis, cue, tiny version and metric; log completion, mood and reflection notes by date.
- Track manual demo distance and see daily/month totals. Manual entries are explicitly not GPS verified.
- Community-style notes feed stored in the app database.
- SQLite data model and `/health` check.

## Important prototype limits
- This is not yet a secure multi-user product: authentication, per-user data isolation, account recovery, moderation, and production security need to be implemented before public use.
- The community feed is not a real social network with separate accounts.
- The habit reflection is not a medical service or a live AI model.
- GPS tracking, background location, native Android packaging, push reminders, and real 3D terrain are not included in this revision.
- For durable hosted data, use a persistent disk/database. Never commit credentials or private user data to a public repository.
