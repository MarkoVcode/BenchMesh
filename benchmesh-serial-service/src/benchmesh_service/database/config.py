"""
Database configuration for BenchMesh recording feature.

This module handles database path resolution and configuration for both
web and Electron deployments.
"""

import os
from pathlib import Path


def get_database_path() -> str:
    """
    Resolve database file path based on deployment environment.

    Priority:
    1. BENCHMESH_DATA_DIR environment variable (if set)
    2. ~/.benchmesh/ (default user data directory)

    Returns:
        str: Absolute path to recordings.db file
    """
    # Check for explicit data directory override
    data_dir = os.environ.get('BENCHMESH_DATA_DIR')

    if data_dir:
        db_path = Path(data_dir) / "recordings.db"
    else:
        # Default to ~/.benchmesh/ for all deployments
        db_path = Path.home() / ".benchmesh" / "recordings.db"

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    return str(db_path.absolute())


def get_database_url() -> str:
    """
    Get SQLAlchemy database URL.

    Returns:
        str: SQLAlchemy database URL (sqlite:///)
    """
    db_path = get_database_path()
    return f"sqlite:///{db_path}"


# Database connection settings
DATABASE_CONFIG = {
    "pool_pre_ping": True,  # Verify connections before using
    "pool_recycle": 3600,   # Recycle connections after 1 hour
    "connect_args": {
        "check_same_thread": False,  # Allow multi-threaded access
        "timeout": 30,  # Wait up to 30 seconds for lock
    }
}
