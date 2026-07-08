"""Database connection helpers."""
 
from __future__ import annotations
 
from sqlalchemy import Engine, create_engine, text
 
from src.config import Settings
 
 
def get_engine(settings: Settings) -> Engine:
    """Create a reusable SQLAlchemy engine."""
 
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )
 
 
def test_connection(engine: Engine) -> None:
    """Raise an exception when PostgreSQL cannot be reached."""
 
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
