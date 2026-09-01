import json
import os
import httpx
from datetime import datetime
from dotenv import load_dotenv
from db.queries import save_digest
load_dotenv(override=True)
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM = os.getenv("SENDGRID_FROM")
if not SENDGRID_API_KEY or not SENDGRID_FROM:
    print(
        "SENDGRID_API_KEY and/or SENDGRID_FROM missing from .env — "
        "email sending will fail until both are set. SENDGRID_FROM must "
        "be the exact address you verified in SendGrid's Single Sender "
        "Verification."
    )
def _render_article_card(article: dict, index: int) -> str:
    key_points = article.get("key_points", [])
    if isinstance(key_points, str):
        key_points = json.loads(key_points)
    kp_html = "".join(
        f"<li style='margin:4px 0;color:#4b5563;font-size:13px;'>{p}</li>"
        for p in key_points[:3]
    )
    return f"""
    <div style="border:1px solid #e9d5ff;border-radius:12px;padding:20px;
                margin-bottom:16px;background:#faf5ff;">
        <div style="margin-bottom:10px;">
            <span style="background:#7c3aed;border-radius:50%;width:28px;
                         height:28px;display:inline-flex;align-items:center;
                         justify-content:center;font-weight:700;font-size:13px;
                         color:#ffffff;">#{index}</span>
            <span style="background:#7c3aed30;color:#7c3aed;border-radius:6px;
                         padding:2px 8px;font-size:11px;font-weight:600;
                         text-transform:uppercase;margin-left:8px;">
                {article.get('category', 'other')}
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
def _render_email(user: dict, articles: list[dict]) -> tuple[str, str]:
    date_str = datetime.utcnow().strftime("%A, %B %d %Y")
    name = user.get("name", "there")
    interests = user.get("interests", [])
    if isinstance(interests, str):
        interests = json.loads(interests)
    interests_str = ", ".join(interests[:3])
    cards_html = "".join(
        _render_article_card(article, i) for i, article in enumerate(articles, 1)
    )
    html = f"""
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
            {date_str} · Powered by Llama 3.1 + Groq</p>
    </div>
    <div style="background:#6d28d9;padding:12px 24px;text-align:center;">
        <p style="margin:0;color:#ffffff;font-size:13px;">
            Personalized for <strong>{name}</strong>
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
            AI News Aggregator · Built with LangGraph + Llama 3.1 + Groq<br>
            <a href="#" style="color:#c4b5fd;">Unsubscribe</a> ·
            <a href="#" style="color:#c4b5fd;">Update Interests</a></p>
    </div>
</div>
</body>
</html>"""
    subject = f"Your AI Digest — {date_str}"
    return html, subject
async def send_digest(user: dict, articles: list[dict]) -> str:
    """
    Sends one user's digest email via SendGrid, then records the send
    (or failure) in the digests table. Returns 'sent' or 'failed'.
    """
    html, subject = _render_email(user, articles)
    status = "failed"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "personalizations": [{"to": [{"email": user["email"]}]}],
                    "from": {"email": SENDGRID_FROM},
                    "subject": subject,
                    "content": [{"type": "text/html", "value": html}],
                },
                timeout=30.0,
            )
            if response.status_code == 202:
                status = "sent"
                print(f"Email sent to {user['email']}!")
            else:
                print(f"SendGrid returned {response.status_code} for {user['email']}: {response.text}")
    except Exception as e:
        print(f" Error sending to {user['email']}: {e}")
    article_ids = [a["id"] for a in articles]
    await save_digest(user_id=user["user_id"], article_ids=article_ids, email_status=status)
    return status
async def send_digests(personalized: dict) -> list[str]:
    """
    personalized: { user_id: {"user": {...}, "articles": [...]} } from
    the personalizer agent. Sends one email per user and returns the list
    of email addresses that were successfully sent.
    """
    emails_sent = []
    for user_id, digest in personalized.items():
        status = await send_digest(digest["user"], digest["articles"])
        if status == "sent":
            emails_sent.append(digest["user"]["email"])
    print(f"Emailer done → {len(emails_sent)} emails sent!")
    return emails_sent