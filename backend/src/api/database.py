"""
Database configuration for NEXUS API
Uses SQLAlchemy with SQLite for development, PostgreSQL for production
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Database URL - SQLite for development, can be overridden via environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"sqlite:///{PROJECT_ROOT}/data/nexus.db"
)

# Create engine with appropriate settings
if "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency for getting DB session.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    from . import db_models  # Import models to register them
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
