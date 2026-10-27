# Recruiter Bot — Backend Matching Service

Backend Developer Assignment for **RecruiterFlow Engineering**.

A clean, lightweight backend service that ingests candidate profiles and job openings, then computes and ranks the best matches in both directions (`GET /jobs/{id}/matches` and `GET /candidates/{id}/matches`).

Built with **Python 3.12**, **FastAPI**, and **SQLite**, adhering strictly to the constraint of **100% hand-written raw SQL** (no ORMs, no query builders).

---

## Table of Contents
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Database Schema (Raw SQL)](#database-schema-raw-sql)
- [How to Install & Run Locally](#how-to-install--run-locally)
- [API Reference & Curl Examples](#api-reference--curl-examples)
- [The Matching Algorithm & Design Trade-offs](#the-matching-algorithm--design-trade-offs)
- [Part 2: SQL Detective Challenge](#part-2-sql-detective-challenge)
- [Testing](#testing)
- [AI Tools Usage Note](#ai-tools-usage-note)

---

## Architecture & Tech Stack

- **Language & Framework**: Python 3.12 + FastAPI (provides fast async I/O, automatic OpenAPI docs, and clean validation).
- **Database**: SQLite with standard library `sqlite3` using **hand-written raw SQL** for all DDL and queries.
- **Project Structure**:
  ```
  rf/
  ├── db/
  │   ├── database.py       # Raw SQLite connection, query helpers, and execution
  │   ├── schema.sql        # Hand-written DDL (candidates, jobs, skills, traits, matches)
  │   └── seed.sql          # Hand-written raw SQL seed scripts (15 candidates, 6 jobs)
  ├── routes/
  │   ├── candidates.py     # Endpoints: list, detail, ingest, and reverse matching
  │   ├── jobs.py           # Endpoints: list, detail, ingest, and job-to-candidate matching
  │   └── seed.py           # Endpoint: POST /seed to reset and re-seed
  ├── services/
  │   └── matcher.py        # Raw SQL fetchers, matching algorithm, scoring, and persistence
  ├── main.py               # Application entry point and router registry
  ├── seed.py               # Standalone CLI ingestion script (python seed.py)
  ├── test_api.py           # Automated unit test suite
  ├── sql_detective.sql     # Part 2 SQL Detective queries
  ├── requirements.txt      # Minimal dependencies
  └── README.md             # Complete documentation
  ```

---

## Database Schema (Raw SQL)

The database schema is fully normalized into relational tables with foreign keys and cascade rules:
- `candidates`: Core candidate attributes (`id`, `name`, `experience_years`, `availability`, `quirk`).
- `candidate_skills`: 1-to-many relationship mapping candidate to skills (`candidate_id`, `skill`).
- `candidate_traits`: 1-to-many relationship mapping candidate to personality traits (`candidate_id`, `trait`).
- `jobs`: Core job attributes (`id`, `title`, `min_experience`, `tagline`).
- `job_required_skills`: 1-to-many relationship mapping jobs to required skills (`job_id`, `skill`).
- `job_culture_keywords`: 1-to-many relationship mapping jobs to culture keywords (`job_id`, `keyword`).
- `matches`: Explicit relational table capturing computed matches (`job_id`, `candidate_id`, `score`, `reason`, `matched_at`).

All DDL is located in [`db/schema.sql`](db/schema.sql).

---

## How to Install & Run Locally

### 1. Prerequisites
- Python 3.10+ installed on your machine.
- `git` installed.

### 2. Clone Repository & Install Dependencies
```bash
git clone <repo-url>
cd rf
pip install -r requirements.txt
```

### 3. Initialize & Seed Database
You can initialize and seed the database via CLI:
```bash
python seed.py
```
*(Note: If `recruiter_bot.db` is not present, the FastAPI server will also automatically initialize and seed the database on startup!)*

### 4. Start the Server
```bash
python main.py
# or using uvicorn directly:
uvicorn main:app --reload --port 8000
```
The server will start at: `http://localhost:8000`.

- **Interactive Swagger Docs**: Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.
- **Alternative ReDoc**: Open [http://localhost:8000/redoc](http://localhost:8000/redoc).

---

## API Reference & Curl Examples

### 1. Get Ranked Candidates for a Job
**Endpoint**: `GET /jobs/{id}/matches`  
**Query Parameters**:
- `limit` *(optional, int)*: Maximum number of candidate matches to return.
- `min_score` *(optional, float)*: Minimum match score threshold (0.0 to 100.0).

**Example: Find top candidates for Job 1 ("Backend Detective")**
```bash
curl -X GET "http://localhost:8000/jobs/1/matches?limit=3"
```
**Sample Response**:
```json
{
  "job_id": 1,
  "job_title": "Backend Detective",
  "min_experience": 3,
  "required_skills": ["deduction", "forensics", "pattern-recognition"],
  "total_matches": 3,
  "matches": [
    {
      "candidate_id": 1,
      "candidate_name": "Sherlock H.",
      "experience_years": 8,
      "availability": "Immediate",
      "quirk": "Solves problems by eliminating the impossible; occasionally insufferable in standups.",
      "score": 90.0,
      "reason": "Matched 3/3 required skills (deduction, forensics, pattern-recognition). Exceeds minimum experience (8 yrs vs 3 yrs min). Culture alignment on: analytical. Availability: Immediate.",
      "breakdown": {
        "skills": {
          "score": 50.0,
          "matched": ["deduction", "forensics", "pattern-recognition"],
          "missing": []
        },
        "experience": {
          "score": 22.5,
          "candidate_years": 8,
          "min_required_years": 3
        },
        "culture": {
          "score": 7.5,
          "matched_traits": ["analytical"]
        },
        "availability": {
          "score": 10.0,
          "status": "Immediate"
        }
      }
    },
    {
      "candidate_id": 9,
      "candidate_name": "Sheldon C.",
      "experience_years": 9,
      "availability": "Immediate",
      "score": 49.7,
      "reason": "Matched 1/3 required skills (pattern-recognition). Exceeds minimum experience (9 yrs vs 3 yrs min). Availability: Immediate."
    }
  ]
}
```

---

### 2. Get Ranked Jobs for a Candidate (Reverse Direction)
**Endpoint**: `GET /candidates/{id}/matches`  
**Query Parameters**:
- `limit` *(optional, int)*: Maximum number of job matches to return.
- `min_score` *(optional, float)*: Minimum match score threshold (0.0 to 100.0).

**Example: Find best matching jobs for Candidate 1 ("Sherlock H.")**
```bash
curl -X GET "http://localhost:8000/candidates/1/matches?limit=3"
```
**Sample Response**:
```json
{
  "candidate_id": 1,
  "candidate_name": "Sherlock H.",
  "experience_years": 8,
  "availability": "Immediate",
  "skills": ["deduction", "forensics", "pattern-recognition"],
  "total_matches": 3,
  "matches": [
    {
      "job_id": 1,
      "job_title": "Backend Detective",
      "min_experience": 3,
      "tagline": "We have a bug. We have no leads. We have you.",
      "score": 90.0,
      "reason": "Matched 3/3 required skills (deduction, forensics, pattern-recognition). Exceeds minimum experience (8 yrs vs 3 yrs min). Culture alignment on: analytical. Availability: Immediate."
    }
  ]
}
```

---

### 3. Ingestion Endpoints (Add Candidates & Jobs)

**Add a New Candidate (`POST /candidates`)**:
```bash
curl -X POST "http://localhost:8000/candidates" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alan T.",
    "skills": ["cryptography", "theoretical-analysis", "systems-design"],
    "experience_years": 10,
    "availability": "Immediate",
    "traits": ["rigorous", "visionary"],
    "quirk": "Cracks complex ciphers before morning coffee."
  }'
```

**Add a New Job (`POST /jobs`)**:
```bash
curl -X POST "http://localhost:8000/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Quantum Systems Architect",
    "required_skills": ["cryptography", "systems-design"],
    "min_experience": 6,
    "culture_keywords": ["rigorous", "innovative"],
    "tagline": "Architecting resilient systems for the post-quantum era."
  }'
```

**Reset & Reseed Database (`POST /seed`)**:
```bash
curl -X POST "http://localhost:8000/seed"
```

---

## The Matching Algorithm & Design Trade-offs

### The 4 Pillars of the Scoring Engine
The matching engine maps candidates and jobs onto a normalized **0 to 100 point scale**, distributed across four dimensions:

1. **Skill Overlap (50% Weight / 50 points max)**:
   - Skills represent non-negotiable core competencies.
   - $\text{Skill Score} = 50.0 \times \left( \frac{\text{Matched Required Skills}}{\text{Total Required Skills}} \right)$.
   - If a job has 3 required skills and a candidate has all 3, they receive full 50 points. If 2 out of 3, they receive 33.3 points.

2. **Experience Fit (25% Weight / 25 points max)**:
   - **Meeting or Exceeding Minimum Experience**: If candidate experience $\ge$ minimum experience, the candidate receives a base of 20 points, plus a modest seniority bonus of $+0.5$ points per additional year (capped at $+5$ bonus points).
   - **Experience Deficit**: If candidate experience $<$ minimum experience, they receive partial credit proportional to their experience, capped at 15 points:
     $$\text{Experience Score} = 15.0 \times \left( \frac{\text{Candidate Years}}{\text{Min Required Years}} \right)$$

3. **Culture & Trait Alignment (15% Weight / 15 points max)**:
   - Soft skills and team synergy are compared between candidate traits and job culture keywords (supporting exact and token overlap, such as "calm" aligning with "calm-under-pressure").
   - $\text{Culture Score} = 15.0 \times \min\left(1.0, \frac{\text{Matched Traits}}{\text{Culture Keywords}}\right)$.

4. **Availability Factor (10% Weight / 10 points max)**:
   - In recruiting, turnaround time and candidate responsiveness matter:
     - `Immediate`: **10.0 points** (ready to start immediately).
     - `2 weeks`: **7.0 points** (standard notice period).
     - `Not looking`: **2.0 points** (passive candidate, high friction to recruit).
     - `Other / unspecified`: **5.0 points**.

---

### Key Decisions & Trade-offs

1. **Skill Gating Penalty (Why Woodworkers don't match Backend Detectives)**:
   - *The Dilemma*: If a candidate has 20 years of experience in an unrelated field (e.g. Ron Swanson in woodworking) and applies for "Backend Detective", standard additive scoring would grant them 25 points for experience and 10 points for availability, totaling 35 points despite 0 matching skills.
   - *Our Decision*: When a candidate matches **0 required skills**, a 50% discount penalty is applied to all non-skill attributes. This ensures unqualified candidates naturally rank at the bottom without hiding them from audit logs.

2. **Explainability vs. Black-Box Scoring**:
   - Recruiters rarely trust an arbitrary number like "83.2" without knowing *why*.
   - In addition to the numeric score, our engine produces human-readable, plain-English reasons (e.g., *"Matched 3/3 required skills (deduction, forensics, pattern-recognition). Exceeds minimum experience (8 yrs vs 3 yrs min). Culture alignment on: analytical. Availability: Immediate."*), accompanied by a structured `breakdown` dictionary for UI widgets or client inspection.

3. **Real-time Evaluation with Match Persistence**:
   - Matches are computed dynamically so that any newly created job or candidate is immediately matchable without waiting for batch re-indexing.
   - In tandem, computed matches are upserted into the raw SQL `matches` table (`INSERT ... ON CONFLICT DO UPDATE`), providing a persistent historical record for recruiter analytics and caching.

4. **Deterministic Tie-Breaking**:
   - Ties are broken deterministically by:
     1. `Score` (descending)
     2. `Matched Skills Count` (descending)
     3. `Experience Years` (descending)
     4. `Name / Title` (alphabetical ascending)

---

## Part 2: SQL Detective Challenge

The SQL challenge solutions are provided in [`sql_detective.sql`](sql_detective.sql). Each query was tested and verified against the challenge dataset:

1. **Q1 — Open Job Postings with Owning Recruiter**:
   - Joins `job_postings` with `recruiters` filtered by `status = 'open'`.
   - Identified 4 open postings: Backend Engineer I (Priya Shah), Backend Engineer I (Daniel Ortiz), Backend Engineer II (Priya Shah), DevOps Engineer (Wei Zhang).

2. **Q2 — Final-Stage Applicants per Job Posting**:
   - Uses `LEFT JOIN` and `COUNT(DISTINCT i.applicant_id)` so postings with 0 final-stage applicants (e.g. DevOps Engineer and Data Analyst) correctly return `0` rather than disappearing.

3. **Q3 — People Who Effectively Applied to > 1 Job Posting**:
   - **Detective Finding**: The `applicants` table contains dirty data:
     - Applicant ID 1: `"Ananya Rao"`, email `"ananya.rao@mail.com"` (interview for Job 1).
     - Applicant ID 2: `"Ananya Rao"`, email `"Ananya.Rao@mail.com"` (interview for Job 4).
     Casing differed (`ananya.rao@mail.com` vs `Ananya.Rao@mail.com`), and application relationships are recorded in `interviews`.
   - By grouping by `LOWER(TRIM(a.email))` and counting distinct `i.job_posting_id`, we uncover 3 people who applied to multiple jobs:
     - **Ananya Rao** (Job 1 & Job 4)
     - **Ben Turner** (Job 1 & Job 3)
     - **Elena Popescu** (Job 2 & Job 7)

4. **Q4 — Recruiter Final-Stage Conversion Rate ($\ge 3$ Final Interviews)**:
   - Aggregates final-stage interviews per recruiter, computing `passed ÷ total`.
   - Recruiters meeting the $\ge 3$ threshold:
     - **Priya Shah**: 4 final interviews, 3 passed $\rightarrow$ **75.00%** conversion rate.
     - **Daniel Ortiz**: 4 final interviews, 2 passed $\rightarrow$ **50.00%** conversion rate.

5. **Q5 (Bonus) — Top Recruiter per Department using Window Function**:
   - Uses `DENSE_RANK() OVER (PARTITION BY jp.department ORDER BY COUNT(i.id) DESC)`:
     - **Engineering**: Priya Shah (3 successful placements).
     - **Data**: Fatima Al-Sayed (1 successful placement).

---

## Testing

An automated test suite is included in `test_api.py`. It tests:
- Root overview and health endpoints.
- Retrieval of jobs and candidates.
- 404 error handling for non-existent IDs.
- Matching accuracy (verifying Sherlock Holmes is #1 for Backend Detective).
- Query filtering (`limit`, `min_score`).
- Reverse matching (candidate to jobs).
- End-to-end ingestion of new jobs and candidates with raw SQL.
- Match table persistence.

To run the tests:
```bash
python test_api.py
```

---

## AI Tools Usage Note

In the spirit of complete transparency as requested in the assignment:
- **AI Tool Used**: Google Antigravity / Gemini coding assistant.
- **Where it was used**:
  - Scaffolding the initial raw SQL DDL script and normalizing candidate/job seed data into SQL INSERT statements.
  - Formulating the initial test cases in `test_api.py` and reviewing SQLite edge cases on Windows.
  - Reviewing the SQL Detective dirty data edge cases (such as duplicate applicant emails with varying case sensitivity).
- **Human Guidance & Review**:
  - The design of the 4-tier scoring algorithm, skill-gating penalty logic, weight distribution, and architecture decisions were designed, reviewed, and tuned to reflect real-world recruitment considerations.
