"""
Database models for Chess Intuition Trainer.
9 tables: profiles, chapters, puzzles, batches, attempts, sessions,
puzzle_mastery, badge_definitions, earned_badges.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey, UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False)  # "student" or "parent"
    uscf_rating = Column(Integer, default=0)
    total_xp = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_session_date = Column(String)  # "YYYY-MM-DD"


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    section = Column(String, nullable=False)
    start_page = Column(Integer, nullable=False)
    end_page = Column(Integer, nullable=False)
    puzzle_count = Column(Integer, default=0)
    extraction_status = Column(String, default="pending")  # pending/extracting/review/verified

    puzzles = relationship("Puzzle", back_populates="chapter")


class Puzzle(Base):
    __tablename__ = "puzzles"

    id = Column(Integer, primary_key=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    puzzle_number = Column(Integer, nullable=False)
    fen = Column(Text, nullable=False)
    turn = Column(String, nullable=False)  # "w" or "b"
    solution_san = Column(String, nullable=False)
    solution_uci = Column(String, nullable=False)
    solution_line = Column(Text)
    pdf_page = Column(Integer)
    verified = Column(Integer, default=0)  # 0=unverified, 1=parent-approved
    extraction_confidence = Column(Float, default=0.0)

    chapter = relationship("Chapter", back_populates="puzzles")

    __table_args__ = (
        UniqueConstraint("chapter_id", "puzzle_number", name="uq_chapter_puzzle"),
    )


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    puzzle_ids = Column(JSON, nullable=False)  # Ordered list of puzzle IDs
    total_puzzles = Column(Integer, nullable=False)
    current_circle = Column(Integer, default=1)
    status = Column(String, default="active")  # active/ready_to_graduate/graduated

    profile = relationship("Profile")
    chapter = relationship("Chapter")


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    puzzle_id = Column(Integer, ForeignKey("puzzles.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    circle = Column(Integer, nullable=False)
    success = Column(Integer, nullable=False)  # 1=correct, 0=wrong
    time_taken_ms = Column(Integer, nullable=False)
    user_move = Column(String)  # UCI format
    attempted_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile")
    puzzle = relationship("Puzzle")
    batch = relationship("Batch")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    duration_seconds = Column(Integer, default=0)
    puzzles_attempted = Column(Integer, default=0)
    puzzles_correct = Column(Integer, default=0)
    xp_earned = Column(Integer, default=0)

    profile = relationship("Profile")


class PuzzleMastery(Base):
    __tablename__ = "puzzle_mastery"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    puzzle_id = Column(Integer, ForeignKey("puzzles.id"), nullable=False)
    total_attempts = Column(Integer, default=0)
    total_correct = Column(Integer, default=0)
    total_wrong = Column(Integer, default=0)
    best_time_ms = Column(Integer)
    last_time_ms = Column(Integer)
    first_seen_at = Column(DateTime)
    last_seen_at = Column(DateTime)
    wrong_moves = Column(JSON, default=list)
    ease_factor = Column(Float, default=2.5)
    interval_days = Column(Integer, default=1)
    next_review_date = Column(String)  # "YYYY-MM-DD"

    profile = relationship("Profile")
    puzzle = relationship("Puzzle")

    __table_args__ = (
        UniqueConstraint("profile_id", "puzzle_id", name="uq_profile_puzzle_mastery"),
    )


class BadgeDefinition(Base):
    __tablename__ = "badge_definitions"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)  # e.g. "fork_master"
    name = Column(String, nullable=False)  # e.g. "Fork Master"
    description = Column(Text)
    category = Column(String, nullable=False)  # theme/speed/streak/milestone/improvement
    icon = Column(String)  # emoji or icon name


class EarnedBadge(Base):
    __tablename__ = "earned_badges"

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    badge_id = Column(Integer, ForeignKey("badge_definitions.id"), nullable=False)
    earned_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile")
    badge = relationship("BadgeDefinition")

    __table_args__ = (
        UniqueConstraint("profile_id", "badge_id", name="uq_profile_badge"),
    )
