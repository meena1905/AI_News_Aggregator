# ⚡ AI News Aggregator

> A fully automated AI-powered news digest that scrapes, summarizes, and delivers personalized tech news to your inbox every morning at 7AM IST — no servers, no cost, no effort.

---

## 🚀 What It Does

Every day at **7:00 AM IST**, this pipeline automatically:

1. **Scrapes** the latest AI & tech articles from HackerNews and Dev.to
2. **Summarizes** each article using Llama 3.1 via Groq
3. **Personalizes** the digest based on your interests
4. **Emails** a beautiful HTML digest straight to your inbox

Zero manual effort after setup. 💯

---

## 🛠️ Tech Stack

| Layer | Tool |
|-------|------|
| Scraping | Playwright (Chromium) |
| AI Summarization | Groq (Llama 3.1 8B) |
| Orchestration | LangGraph + LangChain |
| Scheduling | GitHub Actions (free) |
| Database | Supabase (PostgreSQL) |
| Email | Resend |
| Backend | FastAPI + APScheduler |

---

## 📁 Project Structure

```
AI_News_Aggregator/
├── agents/
│   └── scraper_agent.py      # Scrapes HackerNews & Dev.to
├── api/
│   └── main.py               # FastAPI app + full pipeline
├── db/                       # Database schema
├── notebooks/                # Experimentation notebooks
├── .github/
│   └── workflows/
│       └── daily_digest.yml  # GitHub Actions scheduler
├── run_pipeline.py           # Pipeline entry point
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup Guide

### 1. Clone the repo
```bash
git clone https://github.com/meena1905/AI_News_Aggregator.git
cd AI_News_Aggregator
```

### 2. Set up Supabase
- Create a free project at [supabase.com](https://supabase.com)
- Run this SQL to create the users table:

```sql
CREATE TABLE users (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  interests JSONB DEFAULT '[]',
  created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO users (name, email, interests) VALUES (
  'Your Name',
  'your@email.com',
  '["AI", "LLM", "machine learning", "tech"]'
);
```

### 3. Get API Keys
- **Groq:** [console.groq.com](https://console.groq.com) → API Keys
- **Resend:** [resend.com](https://resend.com) → API Keys

### 4. Add GitHub Secrets
Go to your repo → **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|--------|-------|
| `DATABASE_URL` | Your Supabase connection string |
| `GROQ_API_KEY` | Your Groq API key |
| `RESEND_API_KEY` | Your Resend API key |

### 5. That's it! 🎉
The workflow runs automatically every day at 7AM IST via GitHub Actions. No server or hosting needed!

To test manually: **Actions → Daily AI News Digest → Run workflow**

---

## 📧 Sample Email

The digest includes for each article:
- 📌 Title + direct link
- 📝 3-4 sentence AI summary
- ✅ 3 key points
- 🏷️ Category tag
- 🔗 Read Article button

---

## 🔧 Local Development

```bash
pip install -r requirements.txt
playwright install chromium --with-deps
cp .env.example .env  # add your keys
python run_pipeline.py
```

---

## 📄 License

MIT License — feel free to fork and customize!

---

Built with ❤️ using LangGraph + Llama3.1 + Groq
