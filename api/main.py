import asyncio
import asyncpg
import httpx
import json
import os
import uuid
import subprocess
from datetime import datetime
from groq import AsyncGroq
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from contextlib import asynccontextmanager

load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM    = "onboarding@resend.dev"
client_groq    = AsyncGroq(api_key=GROQ_API_KEY)

# ─── Scraper ─────────────────────────────────────────────
async def run_scraper():
    result = subprocess.run(
        ["python", "agents/scraper_agent.py"],
        capture_output=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        encoding="utf-8",
        errors="ignore"
    )
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base_dir, "scraped_articles.json"), encoding="utf-8") as f:
        articles = json.load(f)
    print(f"✅ Scraper done → {len(articles)} articles")
    return articles

# ─── Summarizer ──────────────────────────────────────────
async def run_summarizer(articles):
    summarized = []
    for article in articles:
        try:
            prompt = f"""Analyze this tech article and respond ONLY with valid JSON.
Title: {article['title']}
Source: {article['source']}
Return this JSON:
{{
  "summary": "3-4 sentence detailed summary",
  "key_points": ["point 1", "point 2", "point 3"],
  "sentiment": "positive",
  "category": "llm",
  "relevance_score": 0.8,
  "why_it_matters": "one sentence",
  "tags": ["tag1", "tag2", "tag3"]
}}
Only return JSON. No other text."""

            response = await client_groq.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500,
            )
            raw_text   = response.choices[0].message.content
            json_match = raw_text.find("{")
            json_end   = raw_text.rfind("}") + 1
            if json_match != -1:
                result = json.loads(raw_text[json_match:json_end])
                article["summary"]         = result.get("summary", "")
                article["key_points"]      = result.get("key_points", [])
                article["sentiment"]       = result.get("sentiment", "neutral")
                article["category"]        = result.get("category", "other")
                article["relevance_score"] = result.get("relevance_score", 0.5)
                summarized.append(article)
        except Exception as e:
            continue
    print(f"✅ Summarizer done → {len(summarized)} articles")
    return summarized

# ─── Personalizer ────────────────────────────────────────
async def run_personalizer(articles):
    conn = await asyncpg.connect(DATABASE_URL, ssl="require")
    users = await conn.fetch("SELECT * FROM users")
    await conn.close()
    personalized = {}
    for user in users:
        user = dict(user)
        interests = user['interests']
        if isinstance(interests, str):
            interests = json.loads(interests)
        interests_lower = [i.lower() for i in interests]
        scored = []
        for article in articles:
            score = float(article.get('relevance_score') or 0.5)
            for interest in interests_lower:
                if interest in article['title'].lower():
                    score += 0.3
                if interest in (article.get('summary') or '').lower():
                    score += 0.2
            scored.append({**article, 'personal_score': score})
        scored.sort(key=lambda x: x['personal_score'], reverse=True)
        personalized[user['user_id']] = {
            'user':     user,
            'articles': scored[:10]
        }
    print(f"✅ Personalizer done → {len(personalized)} users")
    return personalized

# ─── Emailer ─────────────────────────────────────────────
async def run_emailer(personalized):
    emails_sent = []
    for user_id, digest in personalized.items():
        user     = digest['user']
        articles = digest['articles']
        try:
            date_str  = datetime.utcnow().strftime("%A, %B %d %Y")
            name      = user.get("name", "there")
            interests = user.get("interests", [])
            if isinstance(interests, str):
                interests = json.loads(interests)
            interests_str = ", ".join(interests[:3])
            cards_html    = ""
            for i, article in enumerate(articles, 1):
                key_points = article.get("key_points", [])
                if isinstance(key_points, str):
                    key_points = json.loads(key_points)
                kp_html = "".join(
                    f"<li style='margin:4px 0;color:#4b5563;font-size:13px;'>{p}</li>"
                    for p in key_points[:3]
                )
                cards_html += f"""
                <div style="border:1px solid #e9d5ff;border-radius:12px;padding:20px;
                            margin-bottom:16px;background:#faf5ff;">
                    <div style="margin-bottom:10px;">
                        <span style="background:#7c3aed;border-radius:50%;width:28px;
                                     height:28px;display:inline-flex;align-items:center;
                                     justify-content:center;font-weight:700;font-size:13px;
                                     color:#ffffff;">#{i}</span>
                        <span style="background:#7c3aed30;color:#7c3aed;border-radius:6px;
                                     padding:2px 8px;font-size:11px;font-weight:600;
                                     text-transform:uppercase;margin-left:8px;">
                            {article.get('category','other')}
                        </span>
                    </div>
                    <h3 style="margin:0 0 8px;font-size:16px;font-weight:600;color:#4c1d95;">
                        <a href="{article['url']}" style="color:#4c1d95;text-decoration:none;">
                            {article['title'][:120]}
                        </a>
                    </h3>
                    <p style="margin:0 0 12px;color:#6b21a8;font-size:14px;line-height:1.6;">
                        {(article.get('summary') or '')[:300]}
                    </p>
                    <ul style="margin:0 0 12px;padding-left:16px;">{kp_html}</ul>
                    <div style="text-align:right;">
                        <a href="{article['url']}"
                           style="background:#7c3aed;color:#ffffff;padding:8px 16px;
                                  border-radius:8px;font-size:13px;font-weight:500;
                                  text-decoration:none;">Read Article →</a>
                    </div>
                </div>"""

            email_html = f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f5f3ff;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<div style="max-width:640px;margin:32px auto;">
    <div style="background:linear-gradient(135deg,#4c1d95 0%,#7c3aed 100%);
                border-radius:16px 16px 0 0;padding:32px;text-align:center;">
        <div style="font-size:40px;margin-bottom:8px;">⚡</div>
        <h1 style="margin:0;color:#ffffff;font-size:26px;font-weight:700;">
            AI News Digest</h1>
        <p style="margin:8px 0 0;color:#e9d5ff;font-size:14px;">
            {date_str} · Powered by Llama3.2 + Groq</p>
    </div>
    <div style="background:#6d28d9;padding:12px 24px;text-align:center;">
        <p style="margin:0;color:#ffffff;font-size:13px;">
            🎯 Personalized for <strong>{name}</strong>
            · Interests: <em>{interests_str}</em></p>
    </div>
    <div style="background:#f5f3ff;padding:24px;">
        <p style="color:#4c1d95;font-size:15px;line-height:1.6;margin:0 0 20px;">
            Good morning <strong>{name}</strong>!
            Here are your top <strong>{len(articles)} AI/tech stories</strong>
            for today. Estimated read time: <strong>5 minutes</strong>.</p>
        {cards_html}
    </div>
    <div style="background:#4c1d95;border-radius:0 0 16px 16px;
                padding:24px;text-align:center;">
        <p style="margin:0;color:#e9d5ff;font-size:12px;line-height:1.8;">
            AI News Aggregator · Built with LangGraph + Llama3.2 + Groq<br>
            <a href="#" style="color:#c4b5fd;">Unsubscribe</a> ·
            <a href="#" style="color:#c4b5fd;">Update Interests</a></p>
    </div>
</div>
</body>
</html>"""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {RESEND_API_KEY}",
                        "Content-Type":  "application/json"
                    },
                    json={
                        "from":    RESEND_FROM,
                        "to":      [user["email"]],
                        "subject": f"⚡ Your AI Digest — {date_str}",
                        "html":    email_html,
                    },
                    timeout=30.0
                )
                if response.status_code == 200:
                    emails_sent.append(user["email"])
                    print(f"✅ Email sent to {user['email']}!")
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    print(f"✅ Emailer done → {len(emails_sent)} emails sent!")
    return emails_sent

# ─── Full Pipeline ───────────────────────────────────────
async def run_full_pipeline():
    print(f"\n🚀 Pipeline started at {datetime.utcnow().strftime('%H:%M:%S')}")
    articles     = await run_scraper()
    summarized   = await run_summarizer(articles)
    personalized = await run_personalizer(summarized)
    emails_sent  = await run_emailer(personalized)
    print(f"🎉 Pipeline done! Emails sent: {len(emails_sent)}")

# ─── FastAPI + Scheduler ─────────────────────────────────
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start scheduler
    # Runs at 7AM IST = 1:30AM UTC
    scheduler.add_job(
        run_full_pipeline,
        CronTrigger(hour=1, minute=30),
        id="daily_digest",
        replace_existing=True,
    )
    scheduler.start()
    print("⏰ Scheduler started!")
    print("   Daily digest runs at 7:00 AM IST")
    yield
    scheduler.shutdown()

app = FastAPI(
    title="AI News Aggregator",
    lifespan=lifespan
)

@app.get("/")
async def home():
    return {
        "status":  "running",
        "message": "AI News Aggregator is live!",
        "time":    datetime.utcnow().isoformat()
    }

@app.post("/trigger")
async def trigger_pipeline():
    print("Manual trigger!")
    asyncio.create_task(run_full_pipeline())
    return {"status": "Pipeline started!"}

@app.get("/health")
async def health():
    return {"status": "ok"}
