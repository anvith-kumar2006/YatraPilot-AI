"""
PostgreSQL database connection and management for YatraPilot AI.
Uses Neon PostgreSQL (https://neon.tech/)
"""

import os
import logging
import psycopg
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages PostgreSQL connection to Neon database."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            database_url: PostgreSQL connection string. If None, uses DATABASE_URL from env.
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL not found in environment variables. "
                "Set DATABASE_URL in .env or pass it as argument."
            )
    
    def get_connection(self):
        """
        Get a new database connection.
        
        Returns:
            psycopg connection object.
            
        Raises:
            psycopg.OperationalError: If connection fails.
        """
        try:
            conn = psycopg.connect(self.database_url)
            return conn
        except psycopg.OperationalError as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    @contextmanager
    def get_cursor(self):
        """
        Context manager for database cursor.
        Automatically commits on success, rolls back on error.
        
        Yields:
            psycopg cursor object.
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            yield cursor
            conn.commit()
            logger.debug("Database transaction committed")
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def test_connection(self) -> bool:
        """
        Test database connectivity.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT current_database(), version();")
                db_name, version = cursor.fetchone()
                logger.info(f"✓ Database: {db_name}")
                logger.info(f"✓ PostgreSQL: {version.split(',')[0]}")
                return True
        except Exception as e:
            logger.error(f"✗ Connection test failed: {e}")
            return False
    
    def init_schema(self):
        """
        Initialize database schema (create tables if they don't exist).
        This is the SINGLE source of truth for the database schema.
        """
        schema_sql = """
-- Trips table: Stores completed travel itineraries and planning data
CREATE TABLE IF NOT EXISTS trips (
    id SERIAL PRIMARY KEY,
    channel_name TEXT NOT NULL,
    destination TEXT NOT NULL,
    start_date TEXT,
    duration_days INTEGER NOT NULL DEFAULT 1,
    travellers INTEGER NOT NULL DEFAULT 1,
    budget_amount REAL,
    currency TEXT DEFAULT 'INR',
    preferences_json TEXT,
    weather_summary_json TEXT,
    attractions_json TEXT,
    itinerary_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'SAVED' CHECK (status IN ('DRAFT', 'SAVED', 'UPDATED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Session state table: Tracks active Agora sessions and tool execution state
CREATE TABLE IF NOT EXISTS session_state (
    channel_name TEXT PRIMARY KEY,
    agent_id TEXT,
    active_itinerary_json TEXT,
    pending_approval_json TEXT,
    last_tools_json TEXT,
    transcript_json TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tool logs table: Audit trail of all tool invocations for debugging
CREATE TABLE IF NOT EXISTS tool_logs (
    id SERIAL PRIMARY KEY,
    channel_name TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    arguments_json TEXT NOT NULL,
    result_summary TEXT,
    status TEXT NOT NULL CHECK (status IN ('SUCCESS', 'FAILURE', 'PENDING')),
    latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_trips_channel ON trips(channel_name);
CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status);
CREATE INDEX IF NOT EXISTS idx_tool_logs_channel ON tool_logs(channel_name);
CREATE INDEX IF NOT EXISTS idx_tool_logs_tool_name ON tool_logs(tool_name);
        """
        
        try:
            with self.get_cursor() as cursor:
                cursor.execute(schema_sql)
                logger.info("✓ Database schema initialized")
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            raise
    
    def clear_session_state(self, channel_name: str):
        """Clear session state when ending a session."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "DELETE FROM session_state WHERE channel_name = %s",
                    (channel_name,)
                )
                logger.info(f"✓ Session state cleared for {channel_name}")
        except Exception as e:
            logger.error(f"Failed to clear session state: {e}")
            raise


# Global database instance
_db = None


def get_db() -> DatabaseConnection:
    """Get the global database instance."""
    global _db
    if _db is None:
        _db = DatabaseConnection()
    return _db


def init_db():
    """Initialize database (create schema, test connection)."""
    db = get_db()
    if db.test_connection():
        db.init_schema()
        try:
            from .transport_db import init_transport_providers_schema
            init_transport_providers_schema()
        except Exception as e:
            logger.warning(f"Transport providers schema init warning: {e}")
        logger.info("✓ Database ready")
        return True
    else:
        logger.error("✗ Database initialization failed")
        return False
