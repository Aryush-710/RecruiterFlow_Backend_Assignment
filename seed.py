#!/usr/bin/env python3
"""
Seed script to initialize and load candidates & jobs into SQLite using raw SQL.
Usage:
    python seed.py
"""

import sys
from db.database import seed_db, query_raw

def main():
    print("[*] Initializing Recruiter Bot database with raw SQL...")
    seed_db()
    
    candidates = query_raw("SELECT id, name, experience_years, availability FROM candidates")
    jobs = query_raw("SELECT id, title, min_experience FROM jobs")
    
    print(f"[+] Successfully seeded {len(candidates)} candidates and {len(jobs)} jobs!")
    print("\n--- Seeded Jobs ---")
    for j in jobs:
        print(f"  [{j['id']}] {j['title']} (Min Exp: {j['min_experience']} yrs)")
        
    print("\n--- Seeded Candidates ---")
    for c in candidates:
        print(f"  [{c['id']}] {c['name']} ({c['experience_years']} yrs exp, Status: {c['availability']})")
    print("\n[+] Database ready at recruiter_bot.db")

if __name__ == "__main__":
    main()
