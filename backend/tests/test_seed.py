"""
Phase 1 RED: Test seeding 22 chapters, 3 profiles, and badge definitions.
"""

from models import Profile, Chapter, BadgeDefinition


def test_seed_creates_22_chapters(seeded_db):
    """22 chapters seeded with correct data."""
    chapters = seeded_db.query(Chapter).all()
    assert len(chapters) == 22


def test_chapter_titles_correct(seeded_db):
    """First and last chapters have expected titles."""
    ch1 = seeded_db.query(Chapter).get(1)
    assert ch1.title == "Forks and Double Attacks"
    assert ch1.section == "TACTICAL ELEMENTS"

    ch22 = seeded_db.query(Chapter).get(22)
    assert ch22.title == "Championship-Level Tactics"
    assert ch22.section == "COMBINATION CHALLENGES"


def test_chapter_page_ranges_valid(seeded_db):
    """All chapters have start_page < end_page."""
    chapters = seeded_db.query(Chapter).all()
    for ch in chapters:
        assert ch.start_page < ch.end_page, f"Chapter {ch.id}: {ch.start_page} >= {ch.end_page}"


def test_seed_creates_3_profiles(seeded_db):
    """4 profiles: Rishi (student), Raghav (student), Raj (parent), Guest (student)."""
    profiles = seeded_db.query(Profile).all()
    assert len(profiles) == 4

    names = {p.name for p in profiles}
    assert names == {"Rishi", "Raghav", "Raj", "Guest"}

    rishi = seeded_db.query(Profile).filter_by(name="Rishi").first()
    assert rishi.role == "student"
    assert rishi.uscf_rating == 1228

    raj = seeded_db.query(Profile).filter_by(name="Raj").first()
    assert raj.role == "parent"


def test_seed_creates_badge_definitions(seeded_db):
    """Badge definitions seeded with correct categories."""
    badges = seeded_db.query(BadgeDefinition).all()
    assert len(badges) >= 33  # 22 theme + 2 speed + 4 streak + 4 milestone + 1 improvement

    categories = {b.category for b in badges}
    assert categories == {"theme", "speed", "streak", "milestone", "improvement"}


def test_seed_theme_badges_match_chapters(seeded_db):
    """22 theme badges exist (one per chapter)."""
    theme_badges = seeded_db.query(BadgeDefinition).filter_by(category="theme").all()
    assert len(theme_badges) == 22


def test_seed_is_idempotent(seeded_db):
    """Running seed twice doesn't create duplicates."""
    from seed import seed_all
    seed_all(seeded_db)
    assert seeded_db.query(Profile).count() == 4
    assert seeded_db.query(Chapter).count() == 22
