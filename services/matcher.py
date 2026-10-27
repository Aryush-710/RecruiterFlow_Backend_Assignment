"""
Matching Engine and Raw SQL Access Service for Recruiter Bot.
All queries are hand-written raw SQL.
"""

from typing import Any, Dict, List, Optional
from db.database import query_raw, execute_raw


def parse_comma_separated(value: Optional[str]) -> List[str]:
    """Helper to parse GROUP_CONCAT results into clean lists."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


# ---------------------------------------------------------------------
# Raw SQL Data Fetchers
# ---------------------------------------------------------------------

def fetch_job_by_id(job_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a single job with required skills and culture keywords using raw SQL."""
    sql = """
    SELECT 
        j.id,
        j.title,
        j.min_experience,
        j.tagline,
        j.created_at,
        GROUP_CONCAT(DISTINCT jrs.skill) AS required_skills_str,
        GROUP_CONCAT(DISTINCT jck.keyword) AS culture_keywords_str
    FROM jobs j
    LEFT JOIN job_required_skills jrs ON j.id = jrs.job_id
    LEFT JOIN job_culture_keywords jck ON j.id = jck.job_id
    WHERE j.id = ?
    GROUP BY j.id;
    """
    rows = query_raw(sql, (job_id,))
    if not rows:
        return None
    
    row = rows[0]
    return {
        "id": row["id"],
        "title": row["title"],
        "min_experience": row["min_experience"],
        "tagline": row["tagline"],
        "created_at": row["created_at"],
        "required_skills": parse_comma_separated(row["required_skills_str"]),
        "culture_keywords": parse_comma_separated(row["culture_keywords_str"])
    }


def fetch_all_jobs() -> List[Dict[str, Any]]:
    """Fetches all jobs with their skills and culture keywords using raw SQL."""
    sql = """
    SELECT 
        j.id,
        j.title,
        j.min_experience,
        j.tagline,
        j.created_at,
        GROUP_CONCAT(DISTINCT jrs.skill) AS required_skills_str,
        GROUP_CONCAT(DISTINCT jck.keyword) AS culture_keywords_str
    FROM jobs j
    LEFT JOIN job_required_skills jrs ON j.id = jrs.job_id
    LEFT JOIN job_culture_keywords jck ON j.id = jck.job_id
    GROUP BY j.id
    ORDER BY j.id ASC;
    """
    rows = query_raw(sql)
    results = []
    for row in rows:
        results.append({
            "id": row["id"],
            "title": row["title"],
            "min_experience": row["min_experience"],
            "tagline": row["tagline"],
            "created_at": row["created_at"],
            "required_skills": parse_comma_separated(row["required_skills_str"]),
            "culture_keywords": parse_comma_separated(row["culture_keywords_str"])
        })
    return results


def fetch_candidate_by_id(candidate_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a single candidate with skills and traits using raw SQL."""
    sql = """
    SELECT 
        c.id,
        c.name,
        c.experience_years,
        c.availability,
        c.quirk,
        c.created_at,
        GROUP_CONCAT(DISTINCT cs.skill) AS skills_str,
        GROUP_CONCAT(DISTINCT ct.trait) AS traits_str
    FROM candidates c
    LEFT JOIN candidate_skills cs ON c.id = cs.candidate_id
    LEFT JOIN candidate_traits ct ON c.id = ct.candidate_id
    WHERE c.id = ?
    GROUP BY c.id;
    """
    rows = query_raw(sql, (candidate_id,))
    if not rows:
        return None
    
    row = rows[0]
    return {
        "id": row["id"],
        "name": row["name"],
        "experience_years": row["experience_years"],
        "availability": row["availability"],
        "quirk": row["quirk"],
        "created_at": row["created_at"],
        "skills": parse_comma_separated(row["skills_str"]),
        "traits": parse_comma_separated(row["traits_str"])
    }


def fetch_all_candidates() -> List[Dict[str, Any]]:
    """Fetches all candidates with their skills and traits using raw SQL."""
    sql = """
    SELECT 
        c.id,
        c.name,
        c.experience_years,
        c.availability,
        c.quirk,
        c.created_at,
        GROUP_CONCAT(DISTINCT cs.skill) AS skills_str,
        GROUP_CONCAT(DISTINCT ct.trait) AS traits_str
    FROM candidates c
    LEFT JOIN candidate_skills cs ON c.id = cs.candidate_id
    LEFT JOIN candidate_traits ct ON c.id = ct.candidate_id
    GROUP BY c.id
    ORDER BY c.id ASC;
    """
    rows = query_raw(sql)
    results = []
    for row in rows:
        results.append({
            "id": row["id"],
            "name": row["name"],
            "experience_years": row["experience_years"],
            "availability": row["availability"],
            "quirk": row["quirk"],
            "created_at": row["created_at"],
            "skills": parse_comma_separated(row["skills_str"]),
            "traits": parse_comma_separated(row["traits_str"])
        })
    return results


def persist_match_record(job_id: int, candidate_id: int, score: float, reason: str) -> None:
    """Persists or updates a calculated match in the matches table using raw SQL."""
    sql = """
    INSERT INTO matches (job_id, candidate_id, score, reason, matched_at)
    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(job_id, candidate_id) DO UPDATE SET
        score = excluded.score,
        reason = excluded.reason,
        matched_at = CURRENT_TIMESTAMP;
    """
    execute_raw(sql, (job_id, candidate_id, score, reason))


# ---------------------------------------------------------------------
# Matching Algorithm & Scoring Engine
# ---------------------------------------------------------------------

def compute_match(candidate: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes candidate-to-job fit score (0 - 100) and human-readable explanation.
    
    Weights:
      1. Skill Overlap: 50%
      2. Experience Fit: 25%
      3. Culture & Trait Alignment: 15%
      4. Availability Factor: 10%
    """
    # 1. Skill Overlap (50 points)
    cand_skills_map = {s.strip().lower(): s for s in candidate.get("skills", [])}
    job_skills_norm = [s.strip().lower() for s in job.get("required_skills", [])]
    
    matched_skills = [cand_skills_map[s] for s in job_skills_norm if s in cand_skills_map]
    missing_skills = [s for s in job.get("required_skills", []) if s.strip().lower() not in cand_skills_map]
    
    total_req = len(job_skills_norm)
    skill_ratio = (len(matched_skills) / total_req) if total_req > 0 else 1.0
    skill_score = round(skill_ratio * 50.0, 2)

    # 2. Experience Fit (25 points)
    cand_exp = candidate.get("experience_years", 0)
    min_exp = job.get("min_experience", 0)
    if cand_exp >= min_exp:
        # Base 20 pts + up to 5 pts bonus for relevant seniority (+0.5 pt per extra year)
        extra_years = cand_exp - min_exp
        exp_score = round(20.0 + min(5.0, extra_years * 0.5), 2)
    else:
        # Deficit: proportional credit capped at 15 pts
        exp_score = round((cand_exp / min_exp) * 15.0, 2) if min_exp > 0 else 15.0

    # 3. Culture & Trait Alignment (15 points)
    cand_traits = candidate.get("traits", [])
    job_culture = job.get("culture_keywords", [])
    
    matched_traits = []
    for trait in cand_traits:
        t_clean = trait.strip().lower()
        for kw in job_culture:
            k_clean = kw.strip().lower()
            if t_clean == k_clean or t_clean in k_clean or k_clean in t_clean:
                matched_traits.append(trait)
                break
                
    culture_ratio = (len(matched_traits) / len(job_culture)) if job_culture else 0.5
    culture_score = round(min(1.0, culture_ratio) * 15.0, 2)

    # 4. Availability Factor (10 points)
    avail = candidate.get("availability", "").strip().lower()
    if "immediate" in avail:
        avail_score = 10.0
    elif "2 week" in avail or "two week" in avail:
        avail_score = 7.0
    elif "not looking" in avail:
        avail_score = 2.0
    else:
        avail_score = 5.0

    # Skill Gating: If candidate has zero matching required skills, penalize peripheral score
    has_zero_skills = (total_req > 0 and len(matched_skills) == 0)
    raw_peripheral = exp_score + culture_score + avail_score
    if has_zero_skills:
        # 50% discount on non-skill attributes when fundamentally unqualified
        peripheral_score = round(raw_peripheral * 0.5, 2)
    else:
        peripheral_score = raw_peripheral

    total_score = round(min(100.0, max(0.0, skill_score + peripheral_score)), 1)

    # Compose informative, human-readable reason
    reasons = []
    if total_req > 0:
        if matched_skills:
            reasons.append(f"Matched {len(matched_skills)}/{total_req} required skills ({', '.join(sorted(matched_skills))})")
        else:
            reasons.append(f"No required skill overlap (0/{total_req} matched)")
    else:
        reasons.append("No specific skills required")

    if cand_exp >= min_exp:
        extra = cand_exp - min_exp
        if extra > 0:
            reasons.append(f"Exceeds minimum experience ({cand_exp} yrs vs {min_exp} yrs min)")
        else:
            reasons.append(f"Meets minimum experience ({cand_exp} yrs vs {min_exp} yrs min)")
    else:
        reasons.append(f"Below minimum experience ({cand_exp} yrs vs {min_exp} yrs min)")

    if matched_traits:
        reasons.append(f"Culture alignment on: {', '.join(sorted(matched_traits))}")

    reasons.append(f"Availability: {candidate.get('availability', 'Unknown')}")

    if has_zero_skills:
        reasons.append("Score discounted due to zero skill overlap")

    reason_str = ". ".join(reasons) + "."

    return {
        "score": total_score,
        "reason": reason_str,
        "matched_skills_count": len(matched_skills),
        "total_required_skills": total_req,
        "breakdown": {
            "skills": {
                "score": skill_score,
                "matched": matched_skills,
                "missing": missing_skills
            },
            "experience": {
                "score": exp_score,
                "candidate_years": cand_exp,
                "min_required_years": min_exp
            },
            "culture": {
                "score": culture_score,
                "matched_traits": matched_traits
            },
            "availability": {
                "score": avail_score,
                "status": candidate.get("availability")
            }
        }
    }


def get_ranked_candidates_for_job(job_id: int, limit: Optional[int] = None, min_score: float = 0.0) -> List[Dict[str, Any]]:
    """
    Ranks all candidates for a specific job opening.
    Returns list of matches ordered by score, skill match count, experience.
    Also caches/persists the match in raw SQL matches table.
    """
    job = fetch_job_by_id(job_id)
    if not job:
        return []

    candidates = fetch_all_candidates()
    matches = []

    for cand in candidates:
        eval_res = compute_match(cand, job)
        if eval_res["score"] >= min_score:
            # Persist match in database
            persist_match_record(job["id"], cand["id"], eval_res["score"], eval_res["reason"])
            
            matches.append({
                "candidate_id": cand["id"],
                "candidate_name": cand["name"],
                "experience_years": cand["experience_years"],
                "availability": cand["availability"],
                "quirk": cand["quirk"],
                "score": eval_res["score"],
                "reason": eval_res["reason"],
                "breakdown": eval_res["breakdown"],
                "_matched_skills_count": eval_res["matched_skills_count"]
            })

    # Sort deterministically
    matches.sort(
        key=lambda x: (
            x["score"],
            x["_matched_skills_count"],
            x["experience_years"],
            -ord(x["candidate_name"][0]) if x["candidate_name"] else 0
        ),
        reverse=True
    )

    # Remove internal sort keys
    for m in matches:
        m.pop("_matched_skills_count", None)

    return matches[:limit] if limit else matches


def get_ranked_jobs_for_candidate(candidate_id: int, limit: Optional[int] = None, min_score: float = 0.0) -> List[Dict[str, Any]]:
    """
    Ranks all open jobs for a specific candidate (reverse match).
    Returns list of matches ordered by score, skill match count, min_experience.
    Also caches/persists the match in raw SQL matches table.
    """
    candidate = fetch_candidate_by_id(candidate_id)
    if not candidate:
        return []

    jobs = fetch_all_jobs()
    matches = []

    for job in jobs:
        eval_res = compute_match(candidate, job)
        if eval_res["score"] >= min_score:
            # Persist match in database
            persist_match_record(job["id"], candidate["id"], eval_res["score"], eval_res["reason"])
            
            matches.append({
                "job_id": job["id"],
                "job_title": job["title"],
                "min_experience": job["min_experience"],
                "tagline": job["tagline"],
                "score": eval_res["score"],
                "reason": eval_res["reason"],
                "breakdown": eval_res["breakdown"],
                "_matched_skills_count": eval_res["matched_skills_count"]
            })

    # Sort deterministically
    matches.sort(
        key=lambda x: (
            x["score"],
            x["_matched_skills_count"],
            x["min_experience"]
        ),
        reverse=True
    )

    # Remove internal sort keys
    for m in matches:
        m.pop("_matched_skills_count", None)

    return matches[:limit] if limit else matches
