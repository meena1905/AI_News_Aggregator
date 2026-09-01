import aiosqlite
import os
import json
from typing import Any
DB_FILE = os.path.join(os.path.dirname(__file__), "..", "articles.db")
class SQLitePool:
    """Mimics asyncpg.Pool interface for SQLite."""
    def __init__(self, db_file: str):
        self.db_file = db_file
    
    def acquire(self):
        """Return a connection context manager (not async)."""
        return SQLiteConnection(self.db_file)
    
    async def close(self):
        """Close all connections (SQLite doesn't need this)."""
        pass
    
    async def fetchval(self, query: str, *args):
        """Fetch a single value."""
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, args)
            row = await cursor.fetchone()
            return row[0] if row else None
    
    async def fetch(self, query: str, *args):
        """Fetch multiple rows."""
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, args)
            return await cursor.fetchall()
    
    async def execute(self, query: str, *args):
        """Execute a statement."""
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute(query, args)
            await db.commit()
    
    async def executemany(self, query: str, args_list):
        """Execute multiple statements."""
        async with aiosqlite.connect(self.db_file) as db:
            await db.executemany(query, args_list)
            await db.commit()
class SQLiteConnection:
    """Mimics asyncpg.Connection interface for SQLite."""
    
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.db = None
    
    async def __aenter__(self):
        self.db = await aiosqlite.connect(self.db_file)
        self.db.row_factory = aiosqlite.Row
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            await self.db.close()
    
    async def fetch(self, query: str, *args):
        """Fetch multiple rows."""
        cursor = await self.db.execute(query, args)
        return await cursor.fetchall()
    
    async def fetchval(self, query: str, *args):
        """Fetch a single value."""
        cursor = await self.db.execute(query, args)
        row = await cursor.fetchone()
        return row[0] if row else None
    
    async def execute(self, query: str, *args):
        """Execute a statement."""
        await self.db.execute(query, args)
        await self.db.commit()
    
    async def executemany(self, query: str, args_list):
        """Execute multiple statements."""
        await self.db.executemany(query, args_list)
        await self.db.commit()
async def create_sqlite_pool() -> SQLitePool:
    """Create a SQLite connection pool."""
    return SQLitePool(DB_FILE)
