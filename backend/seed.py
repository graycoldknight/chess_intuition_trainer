"""
Seed data for Chess Intuition Trainer.
Seeds chapters (from Polgar TOC), profiles, and badge definitions.
"""

from sqlalchemy.orm import Session as DBSession
from models import Profile, Chapter, BadgeDefinition


CHAPTERS = [
    # TACTICAL ELEMENTS section
    {"id": 1, "title": "Forks and Double Attacks", "section": "TACTICAL ELEMENTS", "start_page": 13, "end_page": 30},
    {"id": 2, "title": "Pins and Skewers", "section": "TACTICAL ELEMENTS", "start_page": 31, "end_page": 48},
    {"id": 3, "title": "Deflection and Decoy", "section": "TACTICAL ELEMENTS", "start_page": 49, "end_page": 64},
    {"id": 4, "title": "Discovery and Double Check", "section": "TACTICAL ELEMENTS", "start_page": 65, "end_page": 80},
    {"id": 5, "title": "Removing the Guard", "section": "TACTICAL ELEMENTS", "start_page": 81, "end_page": 96},
    {"id": 6, "title": "Pawn Promotion", "section": "TACTICAL ELEMENTS", "start_page": 97, "end_page": 112},
    {"id": 7, "title": "Overloaded Pieces", "section": "TACTICAL ELEMENTS", "start_page": 113, "end_page": 126},
    {"id": 8, "title": "X-ray and Intermediate Moves", "section": "TACTICAL ELEMENTS", "start_page": 127, "end_page": 142},
    {"id": 9, "title": "Trapped Pieces", "section": "TACTICAL ELEMENTS", "start_page": 143, "end_page": 156},
    {"id": 10, "title": "Zugzwang and Stalemate Themes", "section": "TACTICAL ELEMENTS", "start_page": 157, "end_page": 172},
    # SAVE THE GAME section
    {"id": 11, "title": "Perpetual Check", "section": "SAVE THE GAME", "start_page": 173, "end_page": 186},
    {"id": 12, "title": "Stalemate Saves", "section": "SAVE THE GAME", "start_page": 187, "end_page": 200},
    {"id": 13, "title": "Fortress and Drawing Techniques", "section": "SAVE THE GAME", "start_page": 201, "end_page": 214},
    # CHECKMATE PATTERNS section
    {"id": 14, "title": "Back Rank Mates", "section": "CHECKMATE PATTERNS", "start_page": 215, "end_page": 230},
    {"id": 15, "title": "Knight and Bishop Mates", "section": "CHECKMATE PATTERNS", "start_page": 231, "end_page": 246},
    {"id": 16, "title": "Queen and Rook Mates", "section": "CHECKMATE PATTERNS", "start_page": 247, "end_page": 262},
    {"id": 17, "title": "Pawn and Minor Piece Mates", "section": "CHECKMATE PATTERNS", "start_page": 263, "end_page": 276},
    {"id": 18, "title": "Double Check Mates", "section": "CHECKMATE PATTERNS", "start_page": 277, "end_page": 290},
    # COMBINATION CHALLENGES section
    {"id": 19, "title": "Two-Move Combinations", "section": "COMBINATION CHALLENGES", "start_page": 291, "end_page": 310},
    {"id": 20, "title": "Three-Move Combinations", "section": "COMBINATION CHALLENGES", "start_page": 311, "end_page": 330},
    {"id": 21, "title": "Complex Combinations", "section": "COMBINATION CHALLENGES", "start_page": 331, "end_page": 352},
    {"id": 22, "title": "Championship-Level Tactics", "section": "COMBINATION CHALLENGES", "start_page": 353, "end_page": 376},
]

PROFILES = [
    {"name": "Rishi", "role": "student", "uscf_rating": 1228},
    {"name": "Raghav", "role": "student", "uscf_rating": 1008},
    {"name": "Raj", "role": "parent", "uscf_rating": 0},
    {"name": "Guest", "role": "student", "uscf_rating": 0},
]

BADGE_DEFINITIONS = [
    # Theme mastery (22 badges, one per chapter)
    {"key": "fork_master", "name": "Fork Master", "description": "Graduate Chapter 1: Forks and Double Attacks", "category": "theme", "icon": "fork"},
    {"key": "pin_expert", "name": "Pin Expert", "description": "Graduate Chapter 2: Pins and Skewers", "category": "theme", "icon": "pin"},
    {"key": "deflection_ace", "name": "Deflection Ace", "description": "Graduate Chapter 3: Deflection and Decoy", "category": "theme", "icon": "deflect"},
    {"key": "discovery_pro", "name": "Discovery Pro", "description": "Graduate Chapter 4: Discovery and Double Check", "category": "theme", "icon": "discover"},
    {"key": "guard_remover", "name": "Guard Remover", "description": "Graduate Chapter 5: Removing the Guard", "category": "theme", "icon": "remove"},
    {"key": "promotion_king", "name": "Promotion King", "description": "Graduate Chapter 6: Pawn Promotion", "category": "theme", "icon": "crown"},
    {"key": "overload_master", "name": "Overload Master", "description": "Graduate Chapter 7: Overloaded Pieces", "category": "theme", "icon": "weight"},
    {"key": "xray_vision", "name": "X-ray Vision", "description": "Graduate Chapter 8: X-ray and Intermediate Moves", "category": "theme", "icon": "xray"},
    {"key": "trapper", "name": "Trapper", "description": "Graduate Chapter 9: Trapped Pieces", "category": "theme", "icon": "trap"},
    {"key": "zugzwang_wizard", "name": "Zugzwang Wizard", "description": "Graduate Chapter 10: Zugzwang and Stalemate Themes", "category": "theme", "icon": "wizard"},
    {"key": "perpetual_artist", "name": "Perpetual Artist", "description": "Graduate Chapter 11: Perpetual Check", "category": "theme", "icon": "loop"},
    {"key": "stalemate_savior", "name": "Stalemate Savior", "description": "Graduate Chapter 12: Stalemate Saves", "category": "theme", "icon": "shield"},
    {"key": "fortress_builder", "name": "Fortress Builder", "description": "Graduate Chapter 13: Fortress and Drawing Techniques", "category": "theme", "icon": "castle"},
    {"key": "back_rank_assassin", "name": "Back Rank Assassin", "description": "Graduate Chapter 14: Back Rank Mates", "category": "theme", "icon": "skull"},
    {"key": "knight_bishop_master", "name": "Knight & Bishop Master", "description": "Graduate Chapter 15: Knight and Bishop Mates", "category": "theme", "icon": "knight"},
    {"key": "heavy_hitter", "name": "Heavy Hitter", "description": "Graduate Chapter 16: Queen and Rook Mates", "category": "theme", "icon": "hammer"},
    {"key": "minor_piece_maestro", "name": "Minor Piece Maestro", "description": "Graduate Chapter 17: Pawn and Minor Piece Mates", "category": "theme", "icon": "pawn"},
    {"key": "double_check_destroyer", "name": "Double Check Destroyer", "description": "Graduate Chapter 18: Double Check Mates", "category": "theme", "icon": "bolt"},
    {"key": "two_move_tactician", "name": "Two-Move Tactician", "description": "Graduate Chapter 19: Two-Move Combinations", "category": "theme", "icon": "two"},
    {"key": "three_move_tactician", "name": "Three-Move Tactician", "description": "Graduate Chapter 20: Three-Move Combinations", "category": "theme", "icon": "three"},
    {"key": "complex_solver", "name": "Complex Solver", "description": "Graduate Chapter 21: Complex Combinations", "category": "theme", "icon": "brain"},
    {"key": "champion_tactician", "name": "Champion Tactician", "description": "Graduate Chapter 22: Championship-Level Tactics", "category": "theme", "icon": "trophy"},
    # Speed badges
    {"key": "lightning_reflexes", "name": "Lightning Reflexes", "description": "Solve any puzzle correctly in under 3 seconds", "category": "speed", "icon": "zap"},
    {"key": "speed_demon", "name": "Speed Demon", "description": "Complete a circle with average time under 10 seconds", "category": "speed", "icon": "fire"},
    # Streak badges
    {"key": "streak_3", "name": "On a Roll", "description": "3-day training streak", "category": "streak", "icon": "flame"},
    {"key": "streak_7", "name": "Week Warrior", "description": "7-day training streak", "category": "streak", "icon": "flame2"},
    {"key": "streak_14", "name": "Fortnight Fighter", "description": "14-day training streak", "category": "streak", "icon": "flame3"},
    {"key": "streak_30", "name": "Monthly Master", "description": "30-day training streak", "category": "streak", "icon": "flame4"},
    # Milestone badges
    {"key": "first_solve", "name": "First Solve", "description": "Solve your first puzzle", "category": "milestone", "icon": "star"},
    {"key": "century", "name": "Century", "description": "Solve 100 puzzles", "category": "milestone", "icon": "100"},
    {"key": "five_hundred", "name": "500 Club", "description": "Solve 500 puzzles", "category": "milestone", "icon": "500"},
    {"key": "full_book", "name": "Full Book", "description": "Graduate all 22 chapters", "category": "milestone", "icon": "book"},
    # Improvement badges
    {"key": "half_the_time", "name": "Half the Time", "description": "Circle N average < 50% of Circle 1 average", "category": "improvement", "icon": "chart"},
]


def seed_all(db: DBSession):
    """Seed all data. Idempotent -- skips existing records."""
    _seed_profiles(db)
    _seed_chapters(db)
    _seed_badges(db)
    db.commit()


def _seed_profiles(db: DBSession):
    for p in PROFILES:
        existing = db.query(Profile).filter_by(name=p["name"]).first()
        if not existing:
            db.add(Profile(**p))


def _seed_chapters(db: DBSession):
    for c in CHAPTERS:
        existing = db.query(Chapter).filter_by(id=c["id"]).first()
        if not existing:
            db.add(Chapter(**c))


def _seed_badges(db: DBSession):
    for b in BADGE_DEFINITIONS:
        existing = db.query(BadgeDefinition).filter_by(key=b["key"]).first()
        if not existing:
            db.add(BadgeDefinition(**b))


if __name__ == "__main__":
    from database import SessionLocal, init_db
    init_db()
    db = SessionLocal()
    try:
        seed_all(db)
        print("Database seeded successfully.")
    finally:
        db.close()
