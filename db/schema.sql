-- =====================================================================
-- Recruiter Bot Database Schema (Hand-written Raw SQL DDL)
-- =====================================================================

DROP TABLE IF EXISTS matches;
DROP TABLE IF EXISTS job_culture_keywords;
DROP TABLE IF EXISTS job_required_skills;
DROP TABLE IF EXISTS candidate_traits;
DROP TABLE IF EXISTS candidate_skills;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS candidates;

-- Candidates Table
CREATE TABLE candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    experience_years INTEGER NOT NULL CHECK (experience_years >= 0),
    availability VARCHAR(50) NOT NULL,
    quirk TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Candidate Skills (Normalized 1-to-many)
CREATE TABLE candidate_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    skill VARCHAR(100) NOT NULL,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    UNIQUE(candidate_id, skill)
);

-- Candidate Traits (Normalized 1-to-many)
CREATE TABLE candidate_traits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    trait VARCHAR(100) NOT NULL,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    UNIQUE(candidate_id, trait)
);

-- Jobs Table
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(100) NOT NULL,
    min_experience INTEGER NOT NULL CHECK (min_experience >= 0),
    tagline TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Job Required Skills (Normalized 1-to-many)
CREATE TABLE job_required_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    skill VARCHAR(100) NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    UNIQUE(job_id, skill)
);

-- Job Culture Keywords (Normalized 1-to-many)
CREATE TABLE job_culture_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    UNIQUE(job_id, keyword)
);

-- Match Records Table (Represents computed/persisted matches)
CREATE TABLE matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    candidate_id INTEGER NOT NULL,
    score REAL NOT NULL,
    reason TEXT NOT NULL,
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    UNIQUE(job_id, candidate_id)
);

-- Indexes for performance
CREATE INDEX idx_candidate_skills ON candidate_skills(skill);
CREATE INDEX idx_job_required_skills ON job_required_skills(skill);
CREATE INDEX idx_matches_job_score ON matches(job_id, score DESC);
CREATE INDEX idx_matches_candidate_score ON matches(candidate_id, score DESC);

