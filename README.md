# AI News Aggregator
### Live Link

[AI News Aggregator](https://ai-news-aggregator-6bw5.onrender.com)

A fully automated AI-powered news digest that scrapes, summarizes, and delivers personalized tech news to users every morning.

## What It Does

- Scrapes AI and tech articles from HackerNews and Dev.to.
- Summarizes articles using Groq LLMs.
- Personalizes articles based on user interests.
- Sends daily email digests to users.

## Tech Stack

Python, LangGraph, LangChain, Groq, FastAPI, Supabase PostgreSQL, Playwright, SendGrid, Docker, GitHub Actions.

## Project Structure

```
AI_News_Aggregator/
├── agents/
├── api/
├── db/
├── auth/
├── dashboard/
├── utils/
├── .github/
│   └── workflows/
│       └── daily_digest.yml
├── run_pipeline.py
├── requirements.txt
├── Dockerfile
└── README.md
```

## Setup

Clone the repository and install dependencies:

```
git clone https://github.com/meena1905/AI_News_Aggregator.git
cd AI_News_Aggregator
pip install -r requirements.txt
playwright install chromium
```

Add the required environment variables (e.g. in a `.env` file):

```
DATABASE_URL=
GROQ_API_KEY=
SENDGRID_API_KEY=
SENDGRID_FROM=
SENTRY_DSN=
```

Run the API locally:

```
uvicorn api.main:app --reload
```

Run the news pipeline manually:

```
python run_pipeline.py
```

The daily pipeline is automated using GitHub Actions (`.github/workflows/daily_digest.yml`), which triggers `run_pipeline.py` on a scheduled cron job.

## Deployment

The FastAPI application is containerized with Docker and deployed on Render.

```
docker build -t ai-news-aggregator .
docker run -p 8000:8000 --env-file .env ai-news-aggregator
```

## License

MIT License-Developed by Meenakshi S
