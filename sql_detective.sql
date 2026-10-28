-- =====================================================================
-- RecruiterFlow Backend Developer Assignment — Part 2: SQL Detective
-- =====================================================================

-- ---------------------------------------------------------------------
-- Question 1:
-- ---------------------------------------------------------------------

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
-- ---------------------------------------------------------------------

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
-- ---------------------------------------------------------------------

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
-- ---------------------------------------------------------------------

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
-- ---------------------------------------------------------------------

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

