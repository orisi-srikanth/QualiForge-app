import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings

connect_args = {}
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
