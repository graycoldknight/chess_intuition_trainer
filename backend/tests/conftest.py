"""
Pytest fixtures for Chess Intuition Trainer backend tests.
Each test gets a fresh in-memory SQLite database.
"""

import sys
import os
import pytest

# Add backend directory to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database import Base
import models  # noqa: F401 - registers all models


@pytest.fixture
def test_engine():
    """In-memory SQLite engine with foreign keys enabled.
    Uses StaticPool so all connections share the same in-memory DB,
    which is required for TestClient (runs requests in worker threads).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def test_db(test_engine):
    """Fresh database session for each test."""
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    yield db
    db.close()


@pytest.fixture
def seeded_db(test_db):
    """Database session pre-seeded with chapters, profiles, and badges."""
    from seed import seed_all
    seed_all(test_db)
    return test_db


@pytest.fixture
def test_client(test_engine):
    """FastAPI TestClient with test database.

    Monkey-patches the database module to use the test engine,
    which is more reliable than dependency_overrides for generators.
    """
    from fastapi.testclient import TestClient
    import database

    TestSession = sessionmaker(bind=test_engine)

    # Save originals
    orig_engine = database.engine
    orig_session_local = database.SessionLocal

    # Patch database module to use test engine
    database.engine = test_engine
    database.SessionLocal = TestSession

    # Seed the test database
    from seed import seed_all
    db = TestSession()
    seed_all(db)
    db.close()

    from main import app
    with TestClient(app) as client:
        yield client

    # Restore originals
    database.engine = orig_engine
    database.SessionLocal = orig_session_local
