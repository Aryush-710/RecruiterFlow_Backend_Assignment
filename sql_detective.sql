-- =====================================================================
-- RecruiterFlow Backend Developer Assignment — Part 2: SQL Detective
-- File: sql_detective.sql
-- =====================================================================

-- ---------------------------------------------------------------------
-- Question 1:
-- List all currently open job postings, along with the name of the
-- recruiter who owns each one.
-- ---------------------------------------------------------------------
-- Logic:
-- Filter job_postings where status = 'open' and join with recruiters
-- table on recruiter_id to get the owning recruiter's name.
SELECT 
    jp.id AS job_posting_id,
    jp.title,
    jp.department,
    r.name AS recruiter_name
FROM job_postings jp
JOIN recruiters r ON jp.recruiter_id = r.id
WHERE jp.status = 'open'
ORDER BY jp.id;


-- ---------------------------------------------------------------------
-- Question 2:
-- For each job posting, how many applicants reached the Final interview stage?
-- ---------------------------------------------------------------------
-- Logic:
-- "For each job posting" requires listing all postings, even those with zero
-- applicants reaching the Final stage. We use LEFT JOIN with interviews
-- filtered to stage = 'Final' and COUNT(DISTINCT i.applicant_id) to count unique
-- applicants per posting.
SELECT 
    jp.id AS job_posting_id,
    jp.title,
    COUNT(DISTINCT i.applicant_id) AS final_stage_applicants
FROM job_postings jp
LEFT JOIN interviews i ON jp.id = i.job_posting_id AND i.stage = 'Final'
GROUP BY jp.id, jp.title
ORDER BY jp.id;


-- ---------------------------------------------------------------------
-- Question 3:
-- Find every person who effectively applied to more than one job posting.
-- Careful — the data isn't as clean as it looks.
-- ---------------------------------------------------------------------
-- Detective Findings & Logic:
-- 1. Applicants table contains dirty/duplicate records:
--    - id 1: "Ananya Rao", email "ananya.rao@mail.com" (interview for Job 1)
--    - id 2: "Ananya Rao", email "Ananya.Rao@mail.com" (interview for Job 4)
--    The email casing differs ("ananya.rao@mail.com" vs "Ananya.Rao@mail.com"),
--    causing a naive applicant_id grouping to treat them as two different people.
-- 2. Applications to job postings are linked through the `interviews` table
--    (which maps applicant_id -> job_posting_id).
-- 3. We normalize identity by LOWER(TRIM(a.email)) and count the distinct
--    job_posting_id across all associated interviews.
-- 4. Resulting people who applied to > 1 job posting:
--    - Ananya Rao (Job 1 & Job 4)
--    - Ben Turner (Job 1 & Job 3)
--    - Elena Popescu (Job 2 & Job 7)
SELECT 
    LOWER(TRIM(a.email)) AS email,
    MAX(a.full_name) AS full_name,
    COUNT(DISTINCT i.job_posting_id) AS distinct_jobs_applied
FROM applicants a
JOIN interviews i ON a.id = i.applicant_id
GROUP BY LOWER(TRIM(a.email))
HAVING COUNT(DISTINCT i.job_posting_id) > 1
ORDER BY distinct_jobs_applied DESC, full_name ASC;


-- ---------------------------------------------------------------------
-- Question 4:
-- For each recruiter, compute their Final-stage conversion rate 
-- (passed ÷ total Final-stage interviews), but only include recruiters 
-- with at least 3 Final-stage interviews.
-- ---------------------------------------------------------------------
-- Logic:
-- 1. Link recruiters -> job_postings -> interviews where stage = 'Final'.
-- 2. Aggregate total final interviews: COUNT(i.id).
-- 3. Aggregate passed final interviews: SUM(CASE WHEN i.outcome = 'passed' THEN 1 ELSE 0 END).
-- 4. Conversion rate = passed / total (cast to FLOAT to avoid integer division).
-- 5. Filter for recruiters with at least 3 Final-stage interviews using HAVING COUNT(i.id) >= 3.
SELECT 
    r.id AS recruiter_id,
    r.name AS recruiter_name,
    COUNT(i.id) AS total_final_interviews,
    SUM(CASE WHEN i.outcome = 'passed' THEN 1 ELSE 0 END) AS passed_final_interviews,
    ROUND(CAST(SUM(CASE WHEN i.outcome = 'passed' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(i.id), 4) AS conversion_rate
FROM recruiters r
JOIN job_postings jp ON r.id = jp.recruiter_id
JOIN interviews i ON jp.id = i.job_posting_id
WHERE i.stage = 'Final'
GROUP BY r.id, r.name
HAVING COUNT(i.id) >= 3
ORDER BY conversion_rate DESC, total_final_interviews DESC;


-- ---------------------------------------------------------------------
-- Question 5 (Bonus):
-- Using a window function, find the recruiter with the most successful 
-- placements (passed at Final stage) per department.
-- ---------------------------------------------------------------------
-- Logic:
-- 1. A successful placement is defined as an interview where stage = 'Final' 
--    and outcome = 'passed'.
-- 2. In a CTE, count successful placements grouped by (jp.department, r.id, r.name).
-- 3. Use DENSE_RANK() OVER (PARTITION BY jp.department ORDER BY COUNT(i.id) DESC)
--    to rank recruiters within each department.
-- 4. Select the recruiters with rank = 1.
WITH department_recruiter_placements AS (
    SELECT 
        jp.department,
        r.id AS recruiter_id,
        r.name AS recruiter_name,
        COUNT(i.id) AS successful_placements,
        DENSE_RANK() OVER (
            PARTITION BY jp.department 
            ORDER BY COUNT(i.id) DESC
        ) AS dept_rank
    FROM recruiters r
    JOIN job_postings jp ON r.id = jp.recruiter_id
    JOIN interviews i ON jp.id = i.job_posting_id
    WHERE i.stage = 'Final' AND i.outcome = 'passed'
    GROUP BY jp.department, r.id, r.name
)
SELECT 
    department,
    recruiter_id,
    recruiter_name,
    successful_placements
FROM department_recruiter_placements
WHERE dept_rank = 1
ORDER BY department ASC, recruiter_id ASC;
