"""
Database Engine & Session Dependency Injection
Configured for SQLite local development and PostgreSQL production deployment.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings

# Handle SQLite vs PostgreSQL URL specifics
connect_args = {}
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    # Ensure directory exists for sqlite file
    if "///" in db_url:
        db_file = db_url.split("///")[-1]
        os.makedirs(os.path.dirname(os.path.abspath(db_file)), exist_ok=True)
else:
    connect_args = {
        "connect_timeout": 10,
        "options": "-c statement_timeout=15000"
    }

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=300
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency injection generator yielding an active SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
