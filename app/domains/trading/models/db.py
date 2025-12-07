"""
Database initialization and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from app.shared.config import config

Base = declarative_base()

# Create engine based on database URL
if config.DATABASE_URL.startswith("sqlite"):
    # SQLite configuration
    engine = create_engine(
        config.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
else:
    # PostgreSQL or other databases
    engine = create_engine(config.DATABASE_URL, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database and create all tables."""
    # Import all models to ensure they are registered
    from app.domains.trading.models.position import Position
    from app.domains.trading.models.trade import Trade
    from app.domains.trading.models.order import Order
    from app.domains.trading.models.performance import Performance

    # Create all tables
    Base.metadata.create_all(bind=engine)


def get_session():
    """Get database session."""
    return SessionLocal()

