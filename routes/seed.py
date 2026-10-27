"""
API routes for database seeding and resetting.
"""

from fastapi import APIRouter
from db.database import seed_db, query_raw

router = APIRouter(tags=["Admin / Ingestion"])


@router.post("/seed", summary="Reset and reseed database with default candidates and jobs")
def seed_database():
    """Wipes and reseeds the database with all default candidates and jobs using raw SQL."""
    seed_db()
    cands_count = query_raw("SELECT COUNT(*) as cnt FROM candidates")[0]["cnt"]
    jobs_count = query_raw("SELECT COUNT(*) as cnt FROM jobs")[0]["cnt"]
    return {
        "status": "success",
        "message": f"Database successfully reset and seeded with {cands_count} candidates and {jobs_count} jobs.",
        "candidates_count": cands_count,
        "jobs_count": jobs_count
    }
