"""
FastAPI application for Chess Intuition Trainer.
"""

import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import database
from database import get_db
from seed import seed_all
from models import Chapter, Puzzle, Profile
import training

app = FastAPI(title="Chess Intuition Trainer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    database.init_db()
    db = database.SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()


@app.get("/")
def health_check():
    return {"status": "ok", "app": "chess-intuition-trainer"}


# --- Chapter & Extraction endpoints ---

@app.get("/api/chapters")
def list_chapters(db: Session = Depends(get_db)):
    chapters = db.query(Chapter).order_by(Chapter.id).all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "section": c.section,
            "start_page": c.start_page,
            "end_page": c.end_page,
            "puzzle_count": c.puzzle_count,
            "extraction_status": c.extraction_status,
        }
        for c in chapters
    ]


def _run_extraction(chapter_id: int):
    """Background task: runs in a fresh DB session so it outlives the request."""
    from extraction import extract_chapter
    db = database.SessionLocal()
    try:
        result = extract_chapter(chapter_id, db)
        return result
    except Exception as e:
        # Status is reset to "pending" inside extract_chapter on failure
        import logging
        logging.getLogger(__name__).error(f"Extraction failed for chapter {chapter_id}: {e}")
    finally:
        db.close()


@app.post("/api/extract-chapter/{chapter_id}")
def start_extraction(chapter_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    chapter = db.query(Chapter).get(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    if chapter.extraction_status == "extracting":
        raise HTTPException(status_code=409, detail="Extraction already in progress")

    chapter.extraction_status = "extracting"
    db.commit()

    background_tasks.add_task(_run_extraction, chapter_id)
    return {"status": "extracting", "chapter_id": chapter_id}


@app.get("/api/puzzles/unverified/{chapter_id}")
def get_unverified_puzzles(chapter_id: int, db: Session = Depends(get_db)):
    puzzles = (
        db.query(Puzzle)
        .filter(Puzzle.chapter_id == chapter_id, Puzzle.verified == 0)
        .order_by(Puzzle.puzzle_number)
        .all()
    )
    return [
        {
            "id": p.id,
            "puzzle_number": p.puzzle_number,
            "fen": p.fen,
            "turn": p.turn,
            "solution_san": p.solution_san,
            "solution_uci": p.solution_uci,
            "solution_line": p.solution_line,
            "pdf_page": p.pdf_page,
            "verified": p.verified,
            "extraction_confidence": p.extraction_confidence,
        }
        for p in puzzles
    ]


@app.put("/api/puzzles/{puzzle_id}/verify")
def verify_puzzle(puzzle_id: int, db: Session = Depends(get_db)):
    puzzle = db.query(Puzzle).get(puzzle_id)
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    puzzle.verified = 1
    db.commit()
    return {"id": puzzle.id, "verified": True}


@app.post("/api/chapters/{chapter_id}/verify-all")
def verify_all_puzzles(chapter_id: int, db: Session = Depends(get_db)):
    puzzles = db.query(Puzzle).filter(Puzzle.chapter_id == chapter_id, Puzzle.verified == 0).all()
    for p in puzzles:
        p.verified = 1

    chapter = db.query(Chapter).get(chapter_id)
    if chapter:
        chapter.extraction_status = "verified"
    db.commit()
    return {"chapter_id": chapter_id, "verified_count": len(puzzles)}


# ---------------------------------------------------------------------------
# Training endpoints
# ---------------------------------------------------------------------------

class CreateBatchRequest(BaseModel):
    profile_id: int
    chapter_id: int


class AttemptRequest(BaseModel):
    profile_id: int
    puzzle_id: int
    batch_id: int
    circle: int
    success: bool
    time_taken_ms: int
    user_move: str


@app.get("/api/training/state/{profile_id}")
def get_training_state(profile_id: int, db: Session = Depends(get_db)):
    return training.get_training_state(profile_id=profile_id, db=db)


@app.get("/api/training/next-puzzle/{profile_id}")
def next_puzzle(profile_id: int, db: Session = Depends(get_db)):
    puzzle = training.get_next_puzzle(profile_id=profile_id, db=db)
    if puzzle is None:
        return {"puzzle": None}
    return {
        "puzzle": {
            "id": puzzle.id,
            "chapter_id": puzzle.chapter_id,
            "puzzle_number": puzzle.puzzle_number,
            "fen": puzzle.fen,
            "turn": puzzle.turn,
            "solution_san": puzzle.solution_san,
            "solution_uci": puzzle.solution_uci,
            "solution_line": puzzle.solution_line,
        }
    }


@app.post("/api/training/attempt")
def record_attempt(req: AttemptRequest, db: Session = Depends(get_db)):
    attempt = training.record_attempt(
        profile_id=req.profile_id,
        puzzle_id=req.puzzle_id,
        batch_id=req.batch_id,
        circle=req.circle,
        success=req.success,
        time_taken_ms=req.time_taken_ms,
        user_move=req.user_move,
        db=db,
    )
    return {"attempt_id": attempt.id, "success": bool(attempt.success)}


@app.post("/api/training/start-session/{profile_id}")
def start_session(profile_id: int, db: Session = Depends(get_db)):
    session = training.start_session(profile_id=profile_id, db=db)
    return {"session_id": session.id, "profile_id": session.profile_id, "started_at": session.started_at.isoformat()}


@app.post("/api/training/end-session/{session_id}")
def end_session(session_id: int, db: Session = Depends(get_db)):
    session = training.end_session(session_id=session_id, db=db)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.id,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "duration_seconds": session.duration_seconds,
        "puzzles_attempted": session.puzzles_attempted,
        "puzzles_correct": session.puzzles_correct,
    }


@app.post("/api/training/create-batch")
def create_batch(req: CreateBatchRequest, db: Session = Depends(get_db)):
    try:
        batch = training.create_batch(profile_id=req.profile_id, chapter_id=req.chapter_id, db=db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "batch_id": batch.id,
        "profile_id": batch.profile_id,
        "chapter_id": batch.chapter_id,
        "total_puzzles": batch.total_puzzles,
        "current_circle": batch.current_circle,
        "status": batch.status,
    }


@app.post("/api/training/approve-graduation/{batch_id}")
def approve_graduation(batch_id: int, db: Session = Depends(get_db)):
    batch = training.approve_graduation(batch_id=batch_id, db=db)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return {"batch_id": batch.id, "status": batch.status}
