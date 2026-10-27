"""
API routes for Job operations and Job matching.
All DB interactions use hand-written raw SQL.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from db.database import execute_raw, query_raw
from services.matcher import (
    fetch_all_jobs,
    fetch_job_by_id,
    get_ranked_candidates_for_job
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


class JobCreate(BaseModel):
    title: str = Field(..., example="Backend Detective")
    required_skills: List[str] = Field(..., example=["deduction", "pattern-recognition", "forensics"])
    min_experience: int = Field(..., ge=0, example=3)
    culture_keywords: List[str] = Field(default=[], example=["analytical", "autonomous"])
    tagline: Optional[str] = Field(None, example="We have a bug. We have no leads. We have you.")


@router.get("", summary="List all jobs")
def list_jobs():
    """Retrieve all jobs with required skills and culture keywords."""
    return fetch_all_jobs()


@router.get("/{job_id}", summary="Get job by ID")
def get_job(job_id: int):
    """Retrieve details for a specific job."""
    job = fetch_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
    return job


@router.post("", status_code=201, summary="Ingest / Create a new job")
def create_job(payload: JobCreate):
    """Ingest a new job opening into the data store using hand-written raw SQL."""
    # 1. Insert main job record
    insert_job_sql = """
    INSERT INTO jobs (title, min_experience, tagline)
    VALUES (?, ?, ?);
    """
    job_id = execute_raw(insert_job_sql, (payload.title, payload.min_experience, payload.tagline))

    # 2. Insert required skills
    insert_skill_sql = """
    INSERT INTO job_required_skills (job_id, skill)
    VALUES (?, ?);
    """
    for skill in payload.required_skills:
        skill_clean = skill.strip().lower()
        if skill_clean:
            execute_raw(insert_skill_sql, (job_id, skill_clean))

    # 3. Insert culture keywords
    insert_kw_sql = """
    INSERT INTO job_culture_keywords (job_id, keyword)
    VALUES (?, ?);
    """
    for kw in payload.culture_keywords:
        kw_clean = kw.strip().lower()
        if kw_clean:
            execute_raw(insert_kw_sql, (job_id, kw_clean))

    return fetch_job_by_id(job_id)


@router.get("/{job_id}/matches", summary="Get ranked candidate matches for a job")
def get_job_matches(
    job_id: int,
    limit: Optional[int] = Query(None, description="Max number of candidate matches to return", ge=1),
    min_score: float = Query(0.0, description="Minimum score threshold (0 - 100)", ge=0.0, le=100.0)
):
    """
    Ranks candidates for a given job opening.
    Accounts for skill overlap, experience fit, culture traits, and availability.
    Returns matches with score, reason, and transparent score breakdown.
    """
    actual_limit = limit if isinstance(limit, int) else None
    actual_min_score = float(min_score) if isinstance(min_score, (int, float)) else 0.0

    job = fetch_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")

    matches = get_ranked_candidates_for_job(job_id, limit=actual_limit, min_score=actual_min_score)

    return {
        "job_id": job["id"],
        "job_title": job["title"],
        "min_experience": job["min_experience"],
        "required_skills": job["required_skills"],
        "total_matches": len(matches),
        "matches": matches
    }
