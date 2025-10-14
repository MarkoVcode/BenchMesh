"""
Database initialization and session management for BenchMesh.

This module provides SQLAlchemy engine, session factory, and database
initialization functions.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from .config import get_database_url, DATABASE_CONFIG

# SQLAlchemy Base for model definitions
Base = declarative_base()

# Global engine and session factory
_engine = None
_SessionLocal = None


def init_database():
    """
    Initialize database engine and create tables.

    This should be called on application startup.
    """
    global _engine, _SessionLocal

    if _engine is not None:
        return  # Already initialized

    # Create engine
    database_url = get_database_url()
    _engine = create_engine(
        database_url,
        **DATABASE_CONFIG
    )

    # Enable foreign keys for SQLite
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create session factory
    _SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_engine
    )

    # Import models to register them with Base
    from benchmesh_service.models import recording  # noqa: F401

    # Create all tables
    Base.metadata.create_all(bind=_engine)


def get_engine() -> Engine:
    """
    Get the SQLAlchemy engine.

    Returns:
        Engine: SQLAlchemy engine instance
    """
    if _engine is None:
        init_database()
    return _engine


def get_session_factory() -> sessionmaker:
    """
    Get the SQLAlchemy session factory.

    Returns:
        sessionmaker: Session factory
    """
    if _SessionLocal is None:
        init_database()
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Yields:
        Session: SQLAlchemy session
    """
    if _SessionLocal is None:
        init_database()

    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with get_db_context() as db:
            # Use db session
            pass

    Yields:
        Session: SQLAlchemy session
    """
    if _SessionLocal is None:
        init_database()

    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def close_database():
    """
    Close database connections and dispose engine.

    This should be called on application shutdown.
    """
    global _engine, _SessionLocal

    if _engine is not None:
        _engine.dispose()
        _engine = None
        _SessionLocal = None
