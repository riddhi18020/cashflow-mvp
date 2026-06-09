from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Use SQLite for local dev — no PostgreSQL needed
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/cashflow.db")

# SQLite needs check_same_thread=False
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_timescaledb(db):
    # TimescaleDB only works with PostgreSQL — skip for SQLite
    if not DATABASE_URL.startswith("sqlite"):
        try:
            db.execute(text("""
                SELECT create_hypertable(
                    'transactions', 'timestamp',
                    if_not_exists => TRUE
                );
            """))
            db.commit()
        except Exception as e:
            print(f"[TimescaleDB] Skipped: {e}")
