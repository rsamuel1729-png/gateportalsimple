# GATE CSE Preparation Portal

Flask CRUD project using MongoDB via PyMongo.

## Run on Windows PowerShell

```powershell
cd C:\Users\USER\Downloads\gata_low_level
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000. The app connects to the local MongoDB service at `mongodb://127.0.0.1:27017`, using database `gate_prep`.

Login is on one page; choose Student or Admin. Students can register and browse eight courses. Admin demo: `admin@gate.local` / `admin123`. Admins can create, view, edit, and delete website/video resources for each course.

Existing student/admin accounts and 17 saved resources were copied from the old SQLite database into MongoDB. The old `gate_prep.db` file is kept as a backup; the app now reads and writes MongoDB.
