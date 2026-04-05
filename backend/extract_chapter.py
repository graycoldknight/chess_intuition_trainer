#!/usr/bin/env python3
"""
Run extraction for a chapter directly (no server needed).
Usage: python3 extract_chapter.py [chapter_id]
Default: chapter 1
"""

import sys
from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal, init_db
import models  # noqa: registers tables
init_db()

from extraction import extract_chapter

chapter_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else None
clear_existing = "--clear" in sys.argv

print(f"Extracting chapter {chapter_id} (limit {max_pages if max_pages else 'none'} pages, clear={clear_existing})...")
db = SessionLocal()
try:
    result = extract_chapter(chapter_id, db, max_pages=max_pages, clear_existing=clear_existing)
    print(result)
finally:
    db.close()
