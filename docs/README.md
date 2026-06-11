# CVForge Docs

Multi-user SaaS that stores one structured "base CV" per user and generates
ATS-friendly, job-tailored CVs + cover letters (DOCX/PDF) using LLMs.

## Index

- [ARCHITECTURE.md](ARCHITECTURE.md) — system overview, stack, request flow, project layout
- [SETUP.md](SETUP.md) — local dev setup for backend + frontend
- [API.md](API.md) — full REST API reference
- [DATA_MODEL.md](DATA_MODEL.md) — database tables, relationships, CV JSON shape
- [BILLING.md](BILLING.md) — credits, plans, Polar payment integration
- [schema.sql](schema.sql) — final, working SQL schema (SQLite + MySQL notes)

## Quick start

```powershell
# backend
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm run dev
```

Backend: http://localhost:8000 (docs at `/docs`)
Frontend: http://localhost:5173
