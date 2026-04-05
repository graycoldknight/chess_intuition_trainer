# Phase 1: Foundation Verification

*2026-04-05T03:39:27Z by Showboat 0.6.1*
<!-- showboat-id: 19daffcb-6086-4474-a46d-1142e2f245b6 -->

Verify database tables, seed data, and API health.

```bash
cd backend && python3 -m pytest tests/test_models.py tests/test_database.py tests/test_seed.py tests/test_main.py -v --tb=no 2>&1 | grep -E '(PASSED|FAILED|ERROR)' | head -30
```

```output
tests/test_models.py::test_all_nine_tables_created PASSED                [  3%]
tests/test_models.py::test_create_profile PASSED                         [  7%]
tests/test_models.py::test_profile_unique_name PASSED                    [ 11%]
tests/test_models.py::test_create_chapter PASSED                         [ 15%]
tests/test_models.py::test_create_puzzle_with_chapter_fk PASSED          [ 19%]
tests/test_models.py::test_puzzle_unique_chapter_number PASSED           [ 23%]
tests/test_models.py::test_puzzle_invalid_chapter_fk PASSED              [ 26%]
tests/test_models.py::test_create_batch PASSED                           [ 30%]
tests/test_models.py::test_create_attempt PASSED                         [ 34%]
tests/test_models.py::test_create_session PASSED                         [ 38%]
tests/test_models.py::test_create_puzzle_mastery PASSED                  [ 42%]
tests/test_models.py::test_puzzle_mastery_unique_constraint PASSED       [ 46%]
tests/test_models.py::test_badge_definitions_and_earned PASSED           [ 50%]
tests/test_models.py::test_earned_badge_unique_constraint PASSED         [ 53%]
tests/test_database.py::test_engine_created PASSED                       [ 57%]
tests/test_database.py::test_engine_connects PASSED                      [ 61%]
tests/test_database.py::test_tables_auto_created PASSED                  [ 65%]
tests/test_database.py::test_session_lifecycle PASSED                    [ 69%]
tests/test_seed.py::test_seed_creates_22_chapters PASSED                 [ 73%]
tests/test_seed.py::test_chapter_titles_correct PASSED                   [ 76%]
tests/test_seed.py::test_chapter_page_ranges_valid PASSED                [ 80%]
tests/test_seed.py::test_seed_creates_3_profiles PASSED                  [ 84%]
tests/test_seed.py::test_seed_creates_badge_definitions PASSED           [ 88%]
tests/test_seed.py::test_seed_theme_badges_match_chapters PASSED         [ 92%]
tests/test_seed.py::test_seed_is_idempotent PASSED                       [ 96%]
tests/test_main.py::test_health_check_returns_200 PASSED                 [100%]
```

Verify table creation and seed data counts.

```bash
cd backend && python3 -c "from sqlalchemy import create_engine, event, inspect; from sqlalchemy.orm import sessionmaker; from database import Base; import models; from seed import seed_all; e = create_engine('sqlite:///:memory:'); event.listen(e, 'connect', lambda c, r: c.cursor().execute('PRAGMA foreign_keys=ON')); Base.metadata.create_all(bind=e); print('Tables:', sorted(inspect(e).get_table_names())); S = sessionmaker(bind=e); db = S(); seed_all(db); from models import Chapter, Profile, BadgeDefinition; print(f'Chapters: {db.query(Chapter).count()}, Profiles: {db.query(Profile).count()}, Badges: {db.query(BadgeDefinition).count()}')"
```

```output
Tables: ['attempts', 'badge_definitions', 'batches', 'chapters', 'earned_badges', 'profiles', 'puzzle_mastery', 'puzzles', 'sessions']
Chapters: 22, Profiles: 3, Badges: 33
```
