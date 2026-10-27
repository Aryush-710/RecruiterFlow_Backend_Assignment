"""
Unit test suite for Recruiter Bot backend.
Tests all endpoints, raw SQL operations, and matching logic directly in-process.
"""

import unittest
from fastapi import HTTPException
from db.database import seed_db, query_raw
from routes.jobs import list_jobs, get_job, create_job, get_job_matches, JobCreate
from routes.candidates import (
    list_candidates,
    get_candidate,
    create_candidate,
    get_candidate_matches,
    CandidateCreate
)
from main import root_overview, health_check


class TestRecruiterBot(unittest.TestCase):
    def setUp(self):
        # Reset and seed database before each test for complete test isolation
        seed_db()

    def test_root_overview(self):
        res = root_overview()
        self.assertEqual(res["status"], "online")
        self.assertEqual(res["counts"]["candidates"], 15)
        self.assertEqual(res["counts"]["jobs"], 6)

    def test_health_check(self):
        res = health_check()
        self.assertEqual(res["status"], "healthy")

    def test_list_jobs(self):
        jobs = list_jobs()
        self.assertEqual(len(jobs), 6)
        titles = [j["title"] for j in jobs]
        self.assertIn("Backend Detective", titles)
        self.assertIn("Rapid Prototyping Engineer", titles)
        self.assertIn("Developer Relations Lead", titles)

    def test_get_job_detail(self):
        job = get_job(1)
        self.assertEqual(job["id"], 1)
        self.assertEqual(job["title"], "Backend Detective")
        self.assertEqual(job["min_experience"], 3)
        self.assertIn("deduction", job["required_skills"])
        self.assertIn("analytical", job["culture_keywords"])

    def test_get_job_not_found(self):
        with self.assertRaises(HTTPException) as ctx:
            get_job(9999)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_list_candidates(self):
        cands = list_candidates()
        self.assertEqual(len(cands), 15)
        names = [c["name"] for c in cands]
        self.assertIn("Sherlock H.", names)
        self.assertIn("Tony S.", names)
        self.assertIn("Elle W.", names)

    def test_get_candidate_detail(self):
        cand = get_candidate(1)
        self.assertEqual(cand["id"], 1)
        self.assertEqual(cand["name"], "Sherlock H.")
        self.assertEqual(cand["experience_years"], 8)
        self.assertEqual(cand["availability"], "Immediate")
        self.assertIn("forensics", cand["skills"])
        self.assertIn("analytical", cand["traits"])

    def test_get_candidate_not_found(self):
        with self.assertRaises(HTTPException) as ctx:
            get_candidate(9999)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_job_matches_ranking(self):
        # Sherlock Holmes must be #1 for Backend Detective (job 1)
        res = get_job_matches(job_id=1, limit=5, min_score=0.0)
        self.assertEqual(res["job_id"], 1)
        matches = res["matches"]
        self.assertGreater(len(matches), 0)

        top_match = matches[0]
        self.assertEqual(top_match["candidate_name"], "Sherlock H.")
        self.assertGreaterEqual(top_match["score"], 85.0)
        self.assertIn("Matched 3/3 required skills", top_match["reason"])
        
        # Check transparent breakdown
        breakdown = top_match["breakdown"]
        self.assertEqual(breakdown["skills"]["score"], 50.0)
        self.assertGreaterEqual(breakdown["experience"]["score"], 20.0)
        self.assertEqual(breakdown["availability"]["score"], 10.0)

    def test_job_matches_with_filters(self):
        res = get_job_matches(job_id=1, limit=2, min_score=40.0)
        matches = res["matches"]
        self.assertLessEqual(len(matches), 2)
        for m in matches:
            self.assertGreaterEqual(m["score"], 40.0)

    def test_candidate_matches_reverse_direction(self):
        # Sherlock H. (candidate 1) searching for jobs -> Backend Detective should be top match
        res = get_candidate_matches(candidate_id=1, limit=3, min_score=0.0)
        self.assertEqual(res["candidate_id"], 1)
        matches = res["matches"]
        self.assertGreater(len(matches), 0)

        top_job = matches[0]
        self.assertEqual(top_job["job_title"], "Backend Detective")
        self.assertGreaterEqual(top_job["score"], 85.0)

    def test_ingestion_new_candidate_and_job(self):
        # Test creating new job via API with raw SQL
        job_in = JobCreate(
            title="Quantum Cryptographer",
            required_skills=["quantum-computing", "cryptography"],
            min_experience=5,
            culture_keywords=["rigorous", "visionary"],
            tagline="Securing the quantum realm."
        )
        new_job = create_job(job_in)
        self.assertIsNotNone(new_job["id"])
        self.assertEqual(new_job["title"], "Quantum Cryptographer")
        self.assertIn("quantum-computing", new_job["required_skills"])

        # Test creating new candidate via API with raw SQL
        cand_in = CandidateCreate(
            name="Alan T.",
            skills=["quantum-computing", "cryptography", "theoretical-analysis"],
            experience_years=10,
            availability="Immediate",
            traits=["rigorous", "visionary"],
            quirk="Cracks complex ciphers before breakfast."
        )
        new_cand = create_candidate(cand_in)
        self.assertIsNotNone(new_cand["id"])
        self.assertEqual(new_cand["name"], "Alan T.")
        self.assertIn("cryptography", new_cand["skills"])

        # Check match between new candidate and new job
        matches_res = get_job_matches(new_job["id"])
        matches = matches_res["matches"]
        self.assertGreater(len(matches), 0)
        self.assertEqual(matches[0]["candidate_id"], new_cand["id"])
        self.assertGreaterEqual(matches[0]["score"], 85.0)

    def test_match_table_persistence(self):
        # Call matching to trigger computation and persistence
        get_job_matches(1)
        # Ensure match records are persisted in the raw SQL matches table
        rows = query_raw("SELECT COUNT(*) as count FROM matches")
        self.assertGreater(rows[0]["count"], 0)


if __name__ == "__main__":
    unittest.main()
