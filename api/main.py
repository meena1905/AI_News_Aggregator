import json
import os
import time
import bcrypt
import secrets
import httpx
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel, EmailStr
from utils.sentry import init_sentry
from agents.workflow import run_pipeline
from agents.emailer_agent import send_digest, SENDGRID_API_KEY, SENDGRID_FROM
from auth.session import (
    create_session,
    set_session_cookie,
    require_user,
    clear_session,
)
from db.database import get_pool
from db.queries import get_recent_digests
IST_OFFSET = timedelta(hours=5, minutes=30)
APP_BASE_URL = os.getenv(
    "APP_BASE_URL",
    "http://127.0.0.1:8000",
)
def _format_digest_date(dt: datetime) -> str:
   

    dt_ist = dt + IST_OFFSET

    hour_12 = dt_ist.hour % 12 or 12
    am_pm = "AM" if dt_ist.hour < 12 else "PM"

    return (
        f"{dt_ist.strftime('%b')} "
        f"{dt_ist.day}, "
        f"{dt_ist.year} · "
        f"{hour_12}:{dt_ist.strftime('%M')} "
        f"{am_pm} IST"
    )
async def _send_reset_email(
    to_email: str,
    reset_link: str,
) -> bool:

    html = f"""
    <div style="
        font-family:-apple-system,sans-serif;
        max-width:480px;
        margin:0 auto;
        padding:32px;
    ">

      <h2 style="color:#4c1d95;">
        Reset your password
      </h2>

      <p style="
          color:#374151;
          font-size:14px;
          line-height:1.6;
      ">
        Click the button below to set a new password.
        This link expires in 1 hour.
      </p>

      <a
        href="{reset_link}"
        style="
          display:inline-block;
          background:#7c3aed;
          color:#fff;
          padding:12px 24px;
          border-radius:8px;
          text-decoration:none;
          font-weight:600;
          margin-top:12px;
        "
      >
        Reset Password
      </a>

      <p style="
          color:#9ca3af;
          font-size:12px;
          margin-top:24px;
      ">
        If you didn't request this, you can safely ignore this email.
      </p>

    </div>
    """
    try:
        async with httpx.AsyncClient() as client:

            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "personalizations": [
                        {
                            "to": [
                                {
                                    "email": to_email
                                }
                            ]
                        }
                    ],
                    "from": {
                        "email": SENDGRID_FROM
                    },
                    "subject": "Reset your password",
                    "content": [
                        {
                            "type": "text/html",
                            "value": html,
                        }
                    ],
                },
                timeout=30.0,
            )

            return response.status_code == 202

    except Exception as e:

        print(
            f"❌ Failed to send reset email: {e}"
        )

        return False
app = FastAPI(
    title="AI News Aggregator"
)
init_sentry()
_allowed_origins_env = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000",
)
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in _allowed_origins_env.split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
def check_rate_limit(
    request: Request,
    bucket: str,
    max_attempts: int,
    window_seconds: int,
):
    """
    Raises 429 if this client IP exceeds the configured limit.
    """

    client_ip = (
        request.client.host
        if request.client
        else "unknown"
    )

    key = f"{bucket}:{client_ip}"

    now = time.time()

    attempts = _rate_limit_store[key]
    attempts[:] = [
        timestamp
        for timestamp in attempts
        if now - timestamp < window_seconds
    ]
    if len(attempts) >= max_attempts:

        raise HTTPException(
            429,
            "Too many attempts — try again in a few minutes",
        )
    attempts.append(now)
@app.get("/api/dashboard")
async def dashboard_stats(request: Request):
    user_id = require_user(request)

    pool = await get_pool()

    async with pool.acquire() as conn:

        total_digests = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM digests
            WHERE user_id = $1
            """,
            user_id,
        )

        total_articles = await conn.fetchval(
            """
            SELECT COUNT(DISTINCT elem)
            FROM digests d,
                 jsonb_array_elements_text(d.article_ids) elem
            WHERE d.user_id = $1
            """,
            user_id,
        )
        now_ist = (
            datetime.utcnow()
            + IST_OFFSET
        )
        month_start_ist = now_ist.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        month_start_utc = (
            month_start_ist
            - IST_OFFSET
        )
        this_month = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM digests
            WHERE sent_at >= $1
              AND user_id = $2
            """,
            month_start_utc,
            user_id,
        )
        sent_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM digests
            WHERE email_status = 'sent'
              AND user_id = $1
            """,
            user_id,
        )
    success_rate = (
        round(
            (sent_count / total_digests) * 100
        )
        if total_digests
        else 100
    )
    recent = await get_recent_digests(
        limit=5,
        user_id=user_id,
    )
    recent_out = [
        {
            "id": str(d["id"]),
            "date": _format_digest_date(
                d["sent_at"]
            ),
            "articles": len(d["articles"]),
            "sent_to": d["user_email"],
            "status": d["email_status"],
        }
        for d in recent
    ]
    return {
        "total_digests": total_digests,
        "total_articles": total_articles,
        "this_month": this_month,
        "success_rate": success_rate,
        "recent_digests": recent_out,
    }
@app.get("/api/digests")
async def list_digests(
    request: Request,
    page: int = 1,
    page_size: int = 15,
    days: int | None = None,
    status_filter: str | None = None,
):
    user_id = require_user(request)

    offset = (
        page - 1
    ) * page_size

    pool = await get_pool()

    params = [user_id]

    where_clauses = [
        "d.user_id = $1"
    ]

    if days is not None:

        where_clauses.append(
            f"d.sent_at >= NOW() - INTERVAL '{int(days)} days'"
        )

    if status_filter:

        params.append(status_filter)

        where_clauses.append(
            f"d.email_status = ${len(params)}"
        )

    where_sql = (
        f"WHERE {' AND '.join(where_clauses)}"
    )

    async with pool.acquire() as conn:

        total = await conn.fetchval(
            f"""
            SELECT COUNT(*)
            FROM digests d
            {where_sql}
            """,
            *params,
        )

        rows = await conn.fetch(
            f"""
            SELECT
                d.id,
                d.sent_at,
                d.article_ids,
                d.email_status,
                u.email AS user_email

            FROM digests d

            JOIN users u
              ON u.user_id = d.user_id

            {where_sql}

            ORDER BY d.sent_at DESC

            LIMIT ${len(params) + 1}
            OFFSET ${len(params) + 2}
            """,
            *params,
            page_size,
            offset,
        )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "digests": [
            {
                "id": str(r["id"]),

                "date": _format_digest_date(
                    r["sent_at"]
                ),

                "articles": len(
                    json.loads(r["article_ids"])
                ),

                "sent_to": r["user_email"],

                "status": r["email_status"],
            }

            for r in rows
        ],
    }
@app.get("/api/digests/{digest_id}")
async def digest_detail(
    digest_id: str,
    request: Request,
):

    user_id = require_user(request)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                d.*,
                u.name AS user_name,
                u.email AS user_email

            FROM digests d

            JOIN users u
              ON u.user_id = d.user_id

            WHERE d.id = $1
              AND d.user_id = $2
            """,
            digest_id,
            user_id,
        )
        if not row:
            raise HTTPException(
                404,
                "Digest not found",
            )
        article_ids = json.loads(
            row["article_ids"]
        )
        articles = []
        if article_ids:
            articles = [
                dict(a)
                for a in await conn.fetch(
                    """
                    SELECT *
                    FROM articles
                    WHERE id = ANY($1::uuid[])
                    """,
                    article_ids,
                )
            ]

    return {
        "id": str(row["id"]),

        "sent_at": row[
            "sent_at"
        ].isoformat(),

        "status": row[
            "email_status"
        ],

        "user_name": row[
            "user_name"
        ],

        "user_email": row[
            "user_email"
        ],

        "articles": articles,
    }
@app.post("/api/digests/{digest_id}/resend")
async def resend_digest(
    digest_id: str,
    request: Request,
):
    user_id = require_user(request)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                article_ids,
                user_id

            FROM digests

            WHERE id = $1
              AND user_id = $2
            """,
            digest_id,
            user_id,
        )

        if not row:

            raise HTTPException(
                404,
                "Digest not found",
            )

        user_row = await conn.fetchrow(
            """
            SELECT *
            FROM users
            WHERE user_id = $1
            """,
            row["user_id"],
        )

        if not user_row:

            raise HTTPException(
                404,
                "User for this digest no longer exists",
            )

        article_ids = json.loads(
            row["article_ids"]
        )

        articles = []

        if article_ids:

            articles = [
                dict(a)

                for a in await conn.fetch(
                    """
                    SELECT *
                    FROM articles
                    WHERE id = ANY($1::uuid[])
                    """,
                    article_ids,
                )
            ]

    if not articles:

        raise HTTPException(
            400,
            "This digest has no articles to resend",
        )

    status = await send_digest(
        dict(user_row),
        articles,
    )

    if status != "sent":

        raise HTTPException(
            502,
            "SendGrid rejected the email — "
            "check your API key and verified sender in .env",
        )

    return {
        "status": "sent",
        "sent_to": user_row["email"],
    }
@app.get("/api/articles")
async def list_articles(
    source: str | None = None,
    limit: int = 20,
):
    pool = await get_pool()
    query = """
        SELECT *
        FROM articles
    """
    params = []
    if source:
        query += """
            WHERE source = $1
        """
        params.append(source)

    query += f"""
        ORDER BY scraped_at DESC
        LIMIT {limit}
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            query,
            *params,
        )

    return {
        "articles": [
            dict(r)
            for r in rows
        ]
    }
@app.get("/api/users/me")
async def current_user(
    request: Request,
):

    user_id = require_user(request)

    pool = await get_pool()

    async with pool.acquire() as conn:

        row = await conn.fetchrow(
            """
            SELECT
                user_id,
                name,
                email,
                interests

            FROM users

            WHERE user_id = $1
            """,
            user_id,
        )

    if not row:

        raise HTTPException(
            404,
            "User not found",
        )

    return dict(row)
@app.get("/api/preferences")
async def get_preferences(
    request: Request,
):

    user_id = require_user(request)

    pool = await get_pool()

    async with pool.acquire() as conn:

        row = await conn.fetchrow(
            """
            SELECT *
            FROM users
            WHERE user_id = $1
            """,
            user_id,
        )

    if not row:

        raise HTTPException(
            404,
            "User not found",
        )

    return dict(row)

@app.patch("/api/preferences")
async def update_preferences(
    request: Request,
    interests: list[str],
):

    user_id = require_user(request)

    pool = await get_pool()

    async with pool.acquire() as conn:

        result = await conn.execute(
            """
            UPDATE users
            SET interests = $1
            WHERE user_id = $2
            """,
            json.dumps(interests),
            user_id,
        )

    if result == "UPDATE 0":

        raise HTTPException(
            404,
            "User not found",
        )

    return {
        "status": "saved",
        "interests": interests,
    }
class SignupRequest(BaseModel):

    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):

    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):

    email: EmailStr


class ResetPasswordRequest(BaseModel):

    token: str
    password: str
@app.post("/api/signup")
async def signup(
    req: SignupRequest,
    request: Request,
):

    check_rate_limit(
        request,
        "signup",
        max_attempts=5,
        window_seconds=3600,
    )

    if len(req.password) < 8:

        raise HTTPException(
            400,
            "Password must be at least 8 characters",
        )

    pool = await get_pool()

    async with pool.acquire() as conn:

        existing = await conn.fetchrow(
            """
            SELECT user_id
            FROM users
            WHERE email = $1
            """,
            req.email,
        )

        if existing:

            raise HTTPException(
                409,
                "An account with this email already exists",
            )

        password_hash = bcrypt.hashpw(
            req.password.encode(),
            bcrypt.gensalt(),
        ).decode()

        row = await conn.fetchrow(
            """
            INSERT INTO users
                (
                    name,
                    email,
                    interests,
                    password_hash
                )

            VALUES
                (
                    $1,
                    $2,
                    '[]',
                    $3
                )

            RETURNING
                user_id,
                name,
                email,
                interests
            """,
            req.name,
            req.email,
            password_hash,
        )

    return {
        "user_id": str(row["user_id"]),
        "name": row["name"],
        "email": row["email"],
    }
@app.post("/api/login")
async def login(
    req: LoginRequest,
    request: Request,
    response: Response,
):

    check_rate_limit(
        request,
        "login",
        max_attempts=10,
        window_seconds=300,
    )

    pool = await get_pool()

    async with pool.acquire() as conn:

        row = await conn.fetchrow(
            """
            SELECT
                user_id,
                name,
                email,
                password_hash

            FROM users

            WHERE email = $1
            """,
            req.email,
        )

    if not row or not row["password_hash"]:

        raise HTTPException(
            401,
            "Invalid email or password",
        )

    if not bcrypt.checkpw(
        req.password.encode(),
        row["password_hash"].encode(),
    ):

        raise HTTPException(
            401,
            "Invalid email or password",
        )
    token = create_session(
        str(row["user_id"])
    )
    set_session_cookie(
        response,
        token,
    )
    return {
        "name": row["name"],
        "email": row["email"],
    }
@app.post("/api/logout")
async def logout(
    request: Request,
    response: Response,
):
    token = request.cookies.get("session_token")

    clear_session(
        response,
        token,
    )

    return {
        "message": "Logged out successfully"
    }
@app.post("/api/forgot-password")
async def forgot_password(
    req: ForgotPasswordRequest,
    request: Request,
):

    check_rate_limit(
        request,
        "forgot_password",
        max_attempts=3,
        window_seconds=3600,
    )

    pool = await get_pool()

    async with pool.acquire() as conn:

        user = await conn.fetchrow(
            """
            SELECT user_id
            FROM users
            WHERE email = $1
            """,
            req.email,
        )

        if user:

            token = secrets.token_urlsafe(32)

            expires = (
                datetime.utcnow()
                + timedelta(hours=1)
            )

            await conn.execute(
                """
                UPDATE users

                SET
                    reset_token = $1,
                    reset_token_expires = $2

                WHERE user_id = $3
                """,
                token,
                expires,
                user["user_id"],
            )

            reset_link = (
                f"{APP_BASE_URL}"
                f"/reset-password.html"
                f"?token={token}"
            )

            await _send_reset_email(
                req.email,
                reset_link,
            )

    return {
        "message":
            "If an account exists for that email, "
            "a reset link has been sent."
    }
@app.post("/api/reset-password")
async def reset_password(
    req: ResetPasswordRequest,
):

    if len(req.password) < 8:

        raise HTTPException(
            400,
            "Password must be at least 8 characters",
        )

    pool = await get_pool()

    async with pool.acquire() as conn:

        user = await conn.fetchrow(
            """
            SELECT
                user_id,
                reset_token_expires

            FROM users

            WHERE reset_token = $1
            """,
            req.token,
        )

        if (
            not user
            or user["reset_token_expires"]
            < datetime.utcnow()
        ):

            raise HTTPException(
                400,
                "This reset link is invalid or has expired",
            )

        password_hash = bcrypt.hashpw(
            req.password.encode(),
            bcrypt.gensalt(),
        ).decode()

        await conn.execute(
            """
            UPDATE users

            SET
                password_hash = $1,
                reset_token = NULL,
                reset_token_expires = NULL

            WHERE user_id = $2
            """,
            password_hash,
            user["user_id"],
        )

    return {
        "message":
            "Password updated successfully"
    }
@app.post("/api/trigger")
async def trigger_pipeline(
    request: Request,
):
    user_id = require_user(request)

    result = await run_pipeline(
        user_id=user_id
    )
    return {
        "emails_sent":
            result.get(
                "emails_sent",
                []
            )
    }

@app.get("/api/health")
async def health():

    return {
        "status": "ok"
    }

_STATIC_DIR = "dashboard/static"


if os.path.isdir(_STATIC_DIR):

    app.mount(
        "/",
        StaticFiles(
            directory=_STATIC_DIR,
            html=True,
        ),
        name="frontend",
    )

else:

    print(
        f"⚠️ '{_STATIC_DIR}' not found — "
        "frontend won't be served, API routes still work"
    )

scheduler = AsyncIOScheduler()
@app.on_event("startup")
async def start_scheduler():

    if (
        os.getenv(
            "ENABLE_IN_APP_SCHEDULER",
            "false",
        ).lower()
        != "true"
    ):
        return

    scheduler.add_job(
        run_pipeline,
        trigger=CronTrigger(
            hour=1,
            minute=30,
        ),
        id="daily_digest",
        replace_existing=True,
    )
    scheduler.start()