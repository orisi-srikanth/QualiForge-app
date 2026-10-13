"""
Database Connection & Session Factory
Provides SQLAlchemy engine, SessionLocal, Base, and get_db dependency injection.
"""
from backend.app.database.session import engine, SessionLocal, Base, get_db

__all__ = ["engine", "SessionLocal", "Base", "get_db"]
