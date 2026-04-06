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
from datetime import datetime
import database
from database import get_db
from seed import seed_all
from models import Chapter, Puzzle, Profile, Session as TrainingSession, BadgeDefinition, EarnedBadge
import training
import gamification

app = FastAPI(title="Chess Intuition Trainer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
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
        # Phase 9: add solution_uci_line column if missing
        from sqlalchemy import text, inspect
        insp = inspect(database.engine)
        columns = [c["name"] for c in insp.get_columns("puzzles")]
        if "solution_uci_line" not in columns:
            db.execute(text("ALTER TABLE puzzles ADD COLUMN solution_uci_line TEXT"))
            db.commit()
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
# Import answers (Phase 9: multi-move)
# ---------------------------------------------------------------------------

class ImportAnswersRequest(BaseModel):
    answers_text: str


@app.post("/api/chapters/{chapter_id}/import-answers")
def import_answers(chapter_id: int, req: ImportAnswersRequest, db: Session = Depends(get_db)):
    """Import answer text for a chapter and parse into UCI move sequences."""
    import re
    from extraction import parse_solution_to_uci

    chapter = db.query(Chapter).get(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Parse answers_text: each line starts with "N. <answer prose>"
    answer_map = {}
    for line in req.answers_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(\d+)\.\s*(.*)", line)
        if m:
            answer_map[int(m.group(1))] = m.group(2)

    puzzles = (
        db.query(Puzzle)
        .filter(Puzzle.chapter_id == chapter_id)
        .order_by(Puzzle.puzzle_number)
        .all()
    )

    total = 0
    parsed = 0
    failed = []

    for p in puzzles:
        answer = answer_map.get(p.puzzle_number)
        if not answer:
            continue
        total += 1
        p.solution_line = answer
        uci_line = parse_solution_to_uci(p.fen, answer)
        if uci_line:
            p.solution_uci_line = uci_line
            parsed += 1
        else:
            failed.append(p.puzzle_number)

    db.commit()
    return {"total": total, "parsed": parsed, "failed": failed}


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
            "solution_uci_line": puzzle.solution_uci_line or [puzzle.solution_uci],
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

    # Calculate XP and update profile
    profile = db.query(Profile).get(req.profile_id)
    streak = profile.current_streak or 0 if profile else 0
    xp = gamification.calculate_xp(
        time_ms=req.time_taken_ms,
        success=req.success,
        circle=req.circle,
        streak=streak,
    )
    if profile:
        profile.total_xp = (profile.total_xp or 0) + xp
        # Also update session xp_earned
        session = training._get_active_session(req.profile_id, db)
        if session:
            session.xp_earned = (session.xp_earned or 0) + xp
        db.commit()

    # Check for newly earned badges
    new_badges = gamification.check_and_award_badges(profile_id=req.profile_id, db=db)
    new_badge_keys = [b.key for b in new_badges]

    return {
        "attempt_id": attempt.id,
        "success": bool(attempt.success),
        "xp_earned": xp,
        "new_badges": new_badge_keys,
    }


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


@app.get("/api/graduations/pending")
def get_pending_graduations(db: Session = Depends(get_db)):
    from models import Batch, Profile, Chapter
    batches = (
        db.query(Batch)
        .filter(Batch.status == "ready_to_graduate")
        .order_by(Batch.id)
        .all()
    )
    result = []
    for b in batches:
        profile = db.query(Profile).get(b.profile_id)
        chapter = db.query(Chapter).get(b.chapter_id)
        result.append({
            "batch_id": b.id,
            "profile_id": b.profile_id,
            "profile_name": profile.name if profile else None,
            "chapter_id": b.chapter_id,
            "chapter_title": chapter.title if chapter else None,
            "current_circle": b.current_circle,
            "status": b.status,
        })
    return result


@app.post("/api/training/approve-graduation/{batch_id}")
def approve_graduation(batch_id: int, db: Session = Depends(get_db)):
    from models import Batch, Chapter
    batch = training.approve_graduation(batch_id=batch_id, db=db)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    # Suggest next chapter (chapter_id + 1 if it exists)
    next_chapter = db.query(Chapter).filter(Chapter.id == batch.chapter_id + 1).first()
    return {
        "batch_id": batch.id,
        "status": batch.status,
        "next_chapter_id": next_chapter.id if next_chapter else None,
    }


# ---------------------------------------------------------------------------
# Dashboard endpoint
# ---------------------------------------------------------------------------

@app.get("/api/dashboard/{profile_id}")
def get_dashboard(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(Profile).get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Training state (includes circle_stats + session_time_remaining_seconds)
    training_state = training.get_training_state(profile_id=profile_id, db=db)

    # Today's aggregated stats across all sessions today
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    today_sessions = (
        db.query(TrainingSession)
        .filter(
            TrainingSession.profile_id == profile_id,
            TrainingSession.started_at >= datetime.strptime(today_str, "%Y-%m-%d"),
        )
        .all()
    )
    today_attempted = sum(s.puzzles_attempted for s in today_sessions)
    today_correct = sum(s.puzzles_correct for s in today_sessions)
    today_duration = sum(
        s.duration_seconds or 0
        for s in today_sessions
        if s.ended_at is not None
    )

    return {
        "profile": {
            "id": profile.id,
            "name": profile.name,
            "total_xp": profile.total_xp or 0,
            "current_streak": profile.current_streak or 0,
            "longest_streak": profile.longest_streak or 0,
            "last_session_date": profile.last_session_date,
        },
        "training": training_state,
        "today": {
            "puzzles_attempted": today_attempted,
            "puzzles_correct": today_correct,
            "duration_seconds": today_duration,
        },
    }


# ---------------------------------------------------------------------------
# Gamification endpoints
# ---------------------------------------------------------------------------

@app.get("/api/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    return gamification.get_leaderboard(db=db)


@app.get("/api/badges/{profile_id}")
def get_badges(profile_id: int, db: Session = Depends(get_db)):
    """Return all badge definitions with earned status for a profile."""
    all_defs = db.query(BadgeDefinition).order_by(BadgeDefinition.id).all()
    earned_ids = {
        eb.badge_id
        for eb in db.query(EarnedBadge).filter(EarnedBadge.profile_id == profile_id).all()
    }
    return [
        {
            "id": b.id,
            "key": b.key,
            "name": b.name,
            "description": b.description,
            "category": b.category,
            "icon": b.icon,
            "earned": b.id in earned_ids,
        }
        for b in all_defs
    ]


@app.get("/api/profiles")
def list_profiles(db: Session = Depends(get_db)):
    profiles = db.query(Profile).order_by(Profile.id).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "role": p.role,
            "uscf_rating": p.uscf_rating,
            "total_xp": p.total_xp or 0,
            "current_streak": p.current_streak or 0,
        }
        for p in profiles
    ]
