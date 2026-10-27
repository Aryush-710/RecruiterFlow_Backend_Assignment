"""
API routes for Candidate operations and Candidate matching.
All DB interactions use hand-written raw SQL.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from db.database import execute_raw, query_raw
from services.matcher import (
    fetch_all_candidates,
    fetch_candidate_by_id,
    get_ranked_jobs_for_candidate
)

router = APIRouter(prefix="/candidates", tags=["Candidates"])


class CandidateCreate(BaseModel):
    name: str = Field(..., example="Sherlock H.")
    skills: List[str] = Field(..., example=["deduction", "pattern-recognition", "forensics"])
    experience_years: int = Field(..., ge=0, example=8)
    availability: str = Field(..., example="Immediate")
    traits: List[str] = Field(default=[], example=["analytical", "blunt"])
    quirk: Optional[str] = Field(None, example="Solves problems by eliminating the impossible; occasionally insufferable in standups.")


@router.get("", summary="List all candidates")
def list_candidates():
    """Retrieve all candidates with their skills and traits."""
    return fetch_all_candidates()


@router.get("/{candidate_id}", summary="Get candidate by ID")
def get_candidate(candidate_id: int):
    """Retrieve details for a specific candidate."""
    cand = fetch_candidate_by_id(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Candidate with ID {candidate_id} not found")
    return cand


@router.post("", status_code=201, summary="Ingest / Create a new candidate")
def create_candidate(payload: CandidateCreate):
    """Ingest a new candidate into the data store using hand-written raw SQL."""
    # 1. Insert main candidate record
    insert_cand_sql = """
    INSERT INTO candidates (name, experience_years, availability, quirk)
    VALUES (?, ?, ?, ?);
    """
    candidate_id = execute_raw(
        insert_cand_sql,
        (payload.name, payload.experience_years, payload.availability, payload.quirk)
    )

    # 2. Insert candidate skills
    insert_skill_sql = """
    INSERT INTO candidate_skills (candidate_id, skill)
    VALUES (?, ?);
    """
    for skill in payload.skills:
        skill_clean = skill.strip().lower()
        if skill_clean:
            execute_raw(insert_skill_sql, (candidate_id, skill_clean))

    # 3. Insert candidate traits
    insert_trait_sql = """
    INSERT INTO candidate_traits (candidate_id, trait)
    VALUES (?, ?);
    """
    for trait in payload.traits:
        trait_clean = trait.strip().lower()
        if trait_clean:
            execute_raw(insert_trait_sql, (candidate_id, trait_clean))

    return fetch_candidate_by_id(candidate_id)


@router.get("/{candidate_id}/matches", summary="Get ranked job matches for a candidate")
def get_candidate_matches(
    candidate_id: int,
    limit: Optional[int] = Query(None, description="Max number of job matches to return", ge=1),
    min_score: float = Query(0.0, description="Minimum score threshold (0 - 100)", ge=0.0, le=100.0)
):
    """
    Ranks open jobs for a given candidate (the reverse direction).
    Accounts for skill overlap, experience fit, culture traits, and availability.
    Returns matches with score, reason, and transparent score breakdown.
    """
    actual_limit = limit if isinstance(limit, int) else None
    actual_min_score = float(min_score) if isinstance(min_score, (int, float)) else 0.0

    cand = fetch_candidate_by_id(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Candidate with ID {candidate_id} not found")

    matches = get_ranked_jobs_for_candidate(candidate_id, limit=actual_limit, min_score=actual_min_score)

    return {
        "candidate_id": cand["id"],
        "candidate_name": cand["name"],
        "experience_years": cand["experience_years"],
        "availability": cand["availability"],
        "skills": cand["skills"],
        "total_matches": len(matches),
        "matches": matches
    }
