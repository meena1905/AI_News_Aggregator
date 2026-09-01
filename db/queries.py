"""
All SQL lives here. Nothing else in the codebase should write raw SQL —
agents call these functions instead, which keeps query logic in one place
and makes the schema easy to find.

Run schema.sql (see db/schema.sql) once against your Supabase project
before using these.
"""
import json
from datetime import datetime
from typing import Iterable
from db.database import get_pool


async def get_users(user_id: str | None = None) -> list[dict]:
    """
    All users by default. Pass user_id to get just that one user back
    (as a single-item list) — used when someone clicks "Send My Digest
    Now" on Preferences, so the pipeline personalizes/emails only the
    person who actually asked for it, not everyone in the database.
    """
    pool = await get_pool()
    if pool is None:
        print("⚠️ Database unavailable - returning empty users list")
        return []
    async with pool.acquire() as conn:
        if user_id is not None:
            rows = await conn.fetch("SELECT * FROM users WHERE user_id = $1", user_id)
        else:
            rows = await conn.fetch("SELECT * FROM users")
    return [dict(r) for r in rows]


async def save_articles(articles: Iterable[dict]) -> int:
    """
    Persist scraped + summarized articles. This is what was previously
    missing entirely — articles used to live only in a local JSON file
    and were discarded after the email send.
    
    If database is unavailable, log warning and continue (graceful degradation).
    """
    pool = await get_pool()
    if pool is None:
        print(f"⚠️ Database unavailable - {len(list(articles))} articles not saved")
        return 0
    
    rows = [
        (
            a["id"],
            a["title"],
            a["url"],
            a["source"],
            a.get("summary"),
            json.dumps(a.get("key_points", [])),
            a.get("sentiment"),
            a.get("category"),
            a.get("relevance_score"),
            datetime.fromisoformat(a["published_at"]),
        )
        for a in articles
    ]
    
    try:
        async with pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO articles
                    (id, title, url, source, summary, key_points, sentiment,
                     category, relevance_score, published_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (id) DO NOTHING
                """,
                rows,
            )
        print(f"✅ Saved {len(rows)} articles to database")
        return len(rows)
    except Exception as e:
        print(f"⚠️ Failed to save articles: {e}")
        return 0


async def save_digest(user_id: str, article_ids: list[str], email_status: str) -> None:
    """Record that a digest was generated/sent for a user, and which articles were in it."""
    pool = await get_pool()
    if pool is None:
        print("⚠️ Database unavailable - digest not recorded")
        return
    
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO digests (user_id, article_ids, email_status)
                VALUES ($1, $2, $3)
                """,
                user_id,
                # str() each id explicitly — the normal pipeline passes
                # plain string ids (from the scraper), but the resend
                # endpoint fetches articles fresh via asyncpg, which
                # returns real uuid.UUID objects for uuid columns.
                # json.dumps() can't serialize those directly, which
                # silently broke every resend's digest-history record
                # (the email itself still sent fine either way).
                json.dumps([str(a) for a in article_ids]),
                email_status,
            )
    except Exception as e:
        print(f"⚠️ Failed to save digest: {e}")


async def get_recent_digests(limit: int = 14, user_id: str | None = None) -> list[dict]:
    """
    Used by the dashboard generator. Joins digests back to their articles
    so we can render a history page without hitting Groq or Playwright again.

    If user_id is given, only that user's digests are returned — this is
    what lets the dashboard show a real per-account history instead of
    every user's digests mixed together.
    """
    pool = await get_pool()
    if pool is None:
        print("⚠️ Database unavailable - returning empty digests")
        return []
    
    try:
        async with pool.acquire() as conn:
            if user_id is not None:
                digest_rows = await conn.fetch(
                    """
                    SELECT d.id, d.sent_at, d.article_ids, d.email_status,
                           u.name AS user_name, u.email AS user_email
                    FROM digests d
                    JOIN users u ON u.user_id = d.user_id
                    WHERE d.user_id = $1
                    ORDER BY d.sent_at DESC
                    LIMIT $2
                    """,
                    user_id, limit,
                )
            else:
                digest_rows = await conn.fetch(
                    """
                    SELECT d.id, d.sent_at, d.article_ids, d.email_status,
                           u.name AS user_name, u.email AS user_email
                    FROM digests d
                    JOIN users u ON u.user_id = d.user_id
                    ORDER BY d.sent_at DESC
                    LIMIT $1
                    """,
                    limit,
                )
            digests = []
            for row in digest_rows:
                row = dict(row)
                article_ids = json.loads(row["article_ids"])
                if article_ids:
                    articles = await conn.fetch(
                        "SELECT * FROM articles WHERE id = ANY($1::uuid[])",
                        article_ids,
                    )
                    row["articles"] = [dict(a) for a in articles]
                else:
                    row["articles"] = []
                digests.append(row)
        return digests
    except Exception as e:
        print(f"⚠️ Failed to get digests: {e}")
        return []