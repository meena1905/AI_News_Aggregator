-- Run this once in the Supabase SQL editor before first use.
CREATE TABLE IF NOT EXISTS users (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  interests JSONB DEFAULT '[]',
  password_hash TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS articles (
  id UUID PRIMARY KEY,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  source TEXT NOT NULL,
  summary TEXT,
  key_points JSONB DEFAULT '[]',
  sentiment TEXT,
  category TEXT,
  relevance_score FLOAT,
  published_at TIMESTAMP,
  scraped_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS digests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(user_id),
  article_ids JSONB DEFAULT '[]',
  email_status TEXT NOT NULL,           -- 'sent' | 'failed'
  sent_at TIMESTAMP DEFAULT NOW()
);
INSERT INTO users (name, email, interests)
VALUES ('Meena S', 'meenakshis3019@email.com', '["AI", "LLM", "machine learning", "tech"]')
ON CONFLICT (email) DO NOTHING;