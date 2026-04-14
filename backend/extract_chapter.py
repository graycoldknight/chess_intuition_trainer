#!/usr/bin/env python3
"""
Run extraction for a chapter directly (no server needed).

Usage:
    python extract_chapter.py 2                   # extract chapter 2 to DB
    python extract_chapter.py 2 --export          # extract + export JSON files
    python extract_chapter.py 2 --clear --export  # re-extract from scratch + export
    python extract_chapter.py --evaluate          # run eval harness on ch1
    python extract_chapter.py --evaluate 2        # run eval harness on ch2
    python extract_chapter.py --report            # quality report for all extracted chapters
"""

import sys
from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal, init_db
import models  # noqa: registers tables
init_db()

# ---------------------------------------------------------------------------
# Parse flags
# ---------------------------------------------------------------------------

args = sys.argv[1:]
do_evaluate = "--evaluate" in args
do_report = "--report" in args
do_export = "--export" in args
clear_existing = "--clear" in args

positional = [a for a in args if not a.startswith("--")]

# ---------------------------------------------------------------------------
# --evaluate: run eval harness
# ---------------------------------------------------------------------------

if do_evaluate:
    chapter_id = int(positional[0]) if positional else 1
    from evaluate_extraction import main as eval_main
    sys.argv = ["evaluate_extraction.py", str(chapter_id)]
    eval_main()
    sys.exit(0)

# ---------------------------------------------------------------------------
# --report: quality report for all chapters with data in DB
# ---------------------------------------------------------------------------

if do_report:
    db = SessionLocal()
    try:
        from models import Chapter, Puzzle
        chapters = db.query(Chapter).order_by(Chapter.id).all()
        print(f"\n{'Ch':>3}  {'Title':<35} {'Status':<12} {'Puzzles':>7} {'Valid%':>7} {'NeedsReview':>12}")
        print("-" * 80)
        for ch in chapters:
            puzzles = db.query(Puzzle).filter_by(chapter_id=ch.id).all()
            if not puzzles:
                print(f"{ch.id:>3}  {ch.title:<35} {'no data':<12}")
                continue
            needs_review = sum(
                1 for p in puzzles
                if p.error_message and p.error_message.startswith("NEEDS_REVIEW")
            )
            valid = sum(1 for p in puzzles if p.extraction_confidence == 1.0)
            pct = f"{valid/len(puzzles):.0%}" if puzzles else "—"
            print(
                f"{ch.id:>3}  {ch.title:<35} {ch.extraction_status:<12} "
                f"{len(puzzles):>7} {pct:>7} {needs_review:>12}"
            )
    finally:
        db.close()
    sys.exit(0)

# ---------------------------------------------------------------------------
# Default: extract chapter (optionally exporting JSON)
# ---------------------------------------------------------------------------

chapter_id = int(positional[0]) if positional else 1
max_pages = int(positional[1]) if len(positional) > 1 else None

db = SessionLocal()
try:
    if do_export:
        from extraction import extract_chapter_to_json
        print(f"Extracting chapter {chapter_id} (limit={max_pages}, clear={clear_existing}) + exporting JSON...")
        if clear_existing:
            from models import Puzzle
            db.query(Puzzle).filter_by(chapter_id=chapter_id).delete()
            db.commit()
            print(f"  Cleared existing puzzles for chapter {chapter_id}")
        report = extract_chapter_to_json(chapter_id, db)
        print(report)
    else:
        from extraction import extract_chapter
        print(f"Extracting chapter {chapter_id} (limit={max_pages}, clear={clear_existing})...")
        result = extract_chapter(chapter_id, db, max_pages=max_pages, clear_existing=clear_existing)
        print(result)
finally:
    db.close()
