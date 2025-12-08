"""
Database connection management for Amazon Price Monitor.
"""

import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager
from typing import Optional, Generator
from config import settings


class DatabaseConnection:
    """Manages MySQL database connections."""

    _instance: Optional['DatabaseConnection'] = None

    def __init__(self):
        self.config = {
            'host': settings.DB_HOST,
            'port': settings.DB_PORT,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
            'database': settings.DB_NAME,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'autocommit': False,
        }
        self._connection: Optional[mysql.connector.MySQLConnection] = None

    @classmethod
    def get_instance(cls) -> 'DatabaseConnection':
        """Get singleton instance of DatabaseConnection."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def connect(self) -> mysql.connector.MySQLConnection:
        """Establish database connection."""
        try:
            if self._connection is None or not self._connection.is_connected():
                self._connection = mysql.connector.connect(**self.config)
            return self._connection
        except Error as e:
            raise ConnectionError(f"Failed to connect to database: {e}")

    def disconnect(self) -> None:
        """Close database connection."""
        if self._connection and self._connection.is_connected():
            self._connection.close()
            self._connection = None

    @contextmanager
    def get_cursor(self, dictionary: bool = True) -> Generator:
        """Context manager for database cursor with automatic commit/rollback."""
        connection = self.connect()
        cursor = connection.cursor(dictionary=dictionary)
        try:
            yield cursor
            connection.commit()
        except Error as e:
            connection.rollback()
            raise e
        finally:
            cursor.close()

    def execute_query(self, query: str, params: tuple = None, fetch: bool = True) -> Optional[list]:
        """Execute a query and optionally fetch results."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            if fetch:
                return cursor.fetchall()
            return None

    def execute_many(self, query: str, params_list: list) -> int:
        """Execute a query with multiple parameter sets."""
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)
            return cursor.rowcount

    def init_database(self) -> None:
        """Initialize database by creating tables if they don't exist."""
        from pathlib import Path

        schema_path = Path(__file__).parent.parent / 'schema.sql'

        # First, connect without database to create it
        config_no_db = self.config.copy()
        del config_no_db['database']

        try:
            conn = mysql.connector.connect(**config_no_db)
            cursor = conn.cursor()

            # Read and execute schema
            with open(schema_path, 'r') as f:
                schema = f.read()

            # Split by semicolon and execute each statement
            statements = [s.strip() for s in schema.split(';') if s.strip()]
            for statement in statements:
                if statement:
                    try:
                        cursor.execute(statement)
                    except Error as e:
                        # Ignore errors for "already exists" etc
                        if e.errno not in [1007, 1050, 1061, 1062]:  # DB/table/index exists
                            print(f"Warning: {e}")

            conn.commit()
            cursor.close()
            conn.close()
            print("Database initialized successfully!")

        except Error as e:
            raise ConnectionError(f"Failed to initialize database: {e}")


def get_db() -> DatabaseConnection:
    """Get database connection instance."""
    return DatabaseConnection.get_instance()
