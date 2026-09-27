from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Force SQLAlchemy to use psycopg (v3) driver instead of psycopg2
# by rewriting the scheme to postgresql+psycopg://
_db_url = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+psycopg://"
).replace(
    "postgresql+psycopg2://", "postgresql+psycopg://"
)

engine = create_engine(_db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
