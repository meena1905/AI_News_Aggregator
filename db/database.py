import os
import asyncpg
from dotenv import load_dotenv
load_dotenv(override=True)
DATABASE_URL = os.getenv("DATABASE_URL")
_pool: asyncpg.Pool | None = None
async def get_pool() -> asyncpg.Pool:
    """Return a shared connection pool, creating it on first use."""
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set — check your .env file")
        _pool = await asyncpg.create_pool(
            DATABASE_URL, ssl="require", min_size=1, max_size=5,
            statement_cache_size=0,  # required when using Supabase's pgbouncer pooler
        )
    return _pool
async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None