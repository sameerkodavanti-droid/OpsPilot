from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver

from app.database.session import engine, Base
from app.api.routes import router, set_pool
from app.config import settings

# Create database schema
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    import psycopg
    
    # psycopg_pool needs a plain libpq connection string (no SQLAlchemy dialect prefix)
    conninfo = (
        settings.DATABASE_URL
        .replace("postgresql+psycopg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )
    
    # Run setup() on a dedicated autocommit connection.
    # PostgresSaver.setup() uses CREATE INDEX CONCURRENTLY which cannot
    # run inside a transaction block — autocommit=True avoids this.
    with psycopg.connect(conninfo, autocommit=True) as setup_conn:
        PostgresSaver(setup_conn).setup()
    
    # Now create the pool used for the actual graph checkpointing
    pool = ConnectionPool(conninfo=conninfo, max_size=20)
    set_pool(pool)
    
    yield
    
    pool.close()

app = FastAPI(title="OpsPilot - Agentic Incident Response System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
def root():
    return {"message": "OpsPilot System is running."}
