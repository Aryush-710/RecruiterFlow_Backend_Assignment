"""
Recruiter Bot — Backend Matching Service
Built for RecruiterFlow Engineering Assignment
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import DB_FILE, init_db, seed_db, query_raw
from routes.candidates import router as candidates_router
from routes.jobs import router as jobs_router
from routes.seed import router as seed_router

# Auto-initialize and seed DB if empty or missing on startup
if not os.path.exists(DB_FILE):
    seed_db()
else:
    try:
        res = query_raw("SELECT COUNT(*) as cnt FROM candidates")
        if res[0]["cnt"] == 0:
            seed_db()
    except Exception:
        seed_db()

app = FastAPI(
    title="Recruiter Bot API",
    description="A backend service that matches candidate profiles and job openings using raw SQL and an explainable scoring engine.",
    version="1.0.0"
)

# Enable CORS for convenience
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(jobs_router)
app.include_router(candidates_router)
app.include_router(seed_router)


@app.get("/", summary="Root Overview & Status")
def root_overview():
    """Returns service overview, system counts, and key API endpoints."""
    try:
        candidates_count = query_raw("SELECT COUNT(*) as cnt FROM candidates")[0]["cnt"]
        jobs_count = query_raw("SELECT COUNT(*) as cnt FROM jobs")[0]["cnt"]
    except Exception:
        candidates_count = 0
        jobs_count = 0

    return {
        "service": "Recruiter Bot API",
        "status": "online",
        "description": "Matching candidate profiles and job openings using pure Raw SQL",
        "counts": {
            "candidates": candidates_count,
            "jobs": jobs_count
        },
        "endpoints": {
            "get_job_matches": "GET /jobs/{id}/matches",
            "get_candidate_matches": "GET /candidates/{id}/matches",
            "list_jobs": "GET /jobs",
            "create_job": "POST /jobs",
            "list_candidates": "GET /candidates",
            "create_candidate": "POST /candidates",
            "reseed_database": "POST /seed",
            "interactive_docs": "/docs",
            "openapi_spec": "/openapi.json"
        }
    }


@app.get("/health", summary="Health Check")
def health_check():
    """Health check endpoint confirming database connectivity."""
    try:
        query_raw("SELECT 1;")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

