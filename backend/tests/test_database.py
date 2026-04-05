"""
Phase 1 RED: Test database engine creation, session lifecycle, table auto-creation.
"""

from sqlalchemy import inspect


def test_engine_created(test_engine):
    """Engine is created and can connect."""
    with test_engine.connect() as conn:
        result = conn.exec_driver_sql("SELECT 1")
        assert result.fetchone()[0] == 1


def test_engine_connects(test_engine):
    """Can execute a query on the engine."""
    with test_engine.connect() as conn:
        result = conn.exec_driver_sql("SELECT 1")
        assert result.fetchone()[0] == 1


def test_tables_auto_created(test_engine):
    """All tables are created when Base.metadata.create_all is called."""
    tables = inspect(test_engine).get_table_names()
    assert len(tables) >= 9


def test_session_lifecycle(test_db):
    """Session can be opened, used, and closed."""
    from models import Profile
    test_db.add(Profile(name="SessionTest", role="student"))
    test_db.commit()
    result = test_db.query(Profile).filter_by(name="SessionTest").first()
    assert result is not None
    # Session cleanup handled by fixture
