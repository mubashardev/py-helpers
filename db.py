from urllib.parse import quote_plus
from sqlmodel import create_engine, Session as SQLModelSession
import os
from sqlalchemy import text
from my_sqlmodel import MySQLModel
from dotenv import load_dotenv

# Import all models to register them with SQLModel metadata
# This must happen before creating the engine
# from models import *

load_dotenv()

# Check if DB_HOST is localhost and set local PostgreSQL credentials
DB_HOST = os.getenv("DB_HOST")
if DB_HOST == "localhost":
    DB_USER = "postgres"
    DB_PASSWORD = quote_plus("32145756")
    DB_NAME = os.getenv("DB_NAME")
    DB_PORT = os.getenv("DB_PORT", "5432")
    if not DB_NAME:
        raise ValueError("DB_NAME must be set in .env for localhost configuration")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    # Prefer a single DATABASE_URL env var (the Neon connection string provided by the user).
    # If not present, fall back to older per-value env vars for compatibility.
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        os.getenv("DB_URL", ""),
    )

    # if not DATABASE_URL:
    #     # As a last fallback, attempt to build from DB_USER/DB_USER_PASSWORD/DB_HOST/DB_NAME
    #     DB_USER = os.getenv("DB_USER")
    #     DB_PASSWORD = quote_plus(os.getenv("DB_USER_PASSWORD") or "")
    #     DB_NAME = os.getenv("DB_NAME")
    #     DB_HOST = os.getenv("DB_HOST")
    #     DB_PORT = os.getenv("DB_PORT", "5432")
        
    #     # Check if running on localhost and set local PostgreSQL credentials
    #     if DB_HOST == "localhost":
    #         DB_USER = "postgres"
    #         DB_PASSWORD = quote_plus("32145756")
    #         DB_HOST = "127.0.0.1"
    #         DB_PORT = "5432"  # Assuming default PostgreSQL port
        
    #     if not all([DB_USER, DB_PASSWORD, DB_NAME, DB_HOST]):
    #         raise ValueError(
    #             "Database configuration is incomplete. Please set DATABASE_URL or DB_USER/DB_USER_PASSWORD/DB_NAME/DB_HOST in .env"
    #         )
    #     DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create the engine with optimized connection pooling
# pool_pre_ping forces a quick SELECT 1 on checkout so dropped SSL connections are recovered transparently.

# Check if using Neon (pooled connection) - they don't support certain startup parameters
is_neon = 'neon.tech' in DATABASE_URL

if is_neon:
    # Neon pooler configuration - simplified connection args
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,  # Neon pooler handles connection pooling
        max_overflow=20,  # Allow up to 30 total connections
        pool_recycle=1800,  # Recycle connections after 30 minutes
        pool_timeout=30,  # Wait up to 30 seconds for a connection
        connect_args={"connect_timeout": 10}
    )
else:
    # Standard PostgreSQL configuration with query timeout
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=20,  # Increased from default 5 to handle more concurrent requests
        max_overflow=40,  # Allow up to 60 total connections (20 + 40)
        pool_recycle=1800,  # Recycle connections after 30 minutes
        pool_timeout=30,  # Wait up to 30 seconds for a connection
        connect_args={
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000"  # 30 second query timeout
        }
    )


def init_db() -> None:
    """Create all tables defined using MySQLModel subclasses if they don't exist.
    
    This function is safe to call on both fresh and existing databases.
    In production, Alembic handles migrations, but this ensures tables exist on startup.
    """
    from sqlalchemy import text
    from sqlalchemy.exc import ProgrammingError, InternalError
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Check which tables already exist in PostgreSQL public schema
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            ))
            existing_tables = set(row[0] for row in result)
        
        # Get all table names from metadata
        metadata_tables = {table.name: table for table in MySQLModel.metadata.tables.values()}
        all_table_names = set(metadata_tables.keys())
        
        # Determine which tables are missing
        missing_table_names = all_table_names - existing_tables
        
        if missing_table_names:
            # Create only the missing tables
            logger.info(f"Database initialization: Creating {len(missing_table_names)} missing table(s)")
            tables_to_create = [metadata_tables[name] for name in missing_table_names]
            
            try:
                MySQLModel.metadata.create_all(engine, tables=tables_to_create)
                logger.info("✓ Database tables created successfully")
            except (ProgrammingError, InternalError) as pe:
                # Handle race conditions where tables/indexes might be created between check and creation
                error_str = str(pe).lower()
                if "already exists" in error_str:
                    logger.info("✓ Database tables verified (objects already exist)")
                else:
                    logger.error(f"✗ Database error: {pe}")
                    raise
        else:
            logger.info("✓ Database ready - all tables verified")
    
    except Exception as e:
        # Only log as error if it's not a duplicate/already exists issue
        error_str = str(e).lower()
        if "already exists" in error_str:
            logger.info("✓ Database initialization completed")
        else:
            logger.error(f"✗ Error during database initialization: {e}")
            raise


def get_session():
    with SQLModelSession(engine) as session:
        yield session