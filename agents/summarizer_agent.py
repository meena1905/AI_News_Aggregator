import json
import os
from groq import AsyncGroq
from dotenv import load_dotenv
load_dotenv(override=True)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
_client: AsyncGroq | None = None
def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=GROQ_API_KEY)
    return _client
SUMMARY_PROMPT = """Analyze this tech article and respond ONLY with valid JSON.
Title: {title}
Source: {source}
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
async def summarize_article(article: dict) -> dict | None:
    """Summarize a single article. Returns None if summarization fails
    (bad JSON from the model, API error, etc.) so the caller can skip it."""
    client = _get_client()
    prompt = SUMMARY_PROMPT.format(title=article["title"], source=article["source"])
    try:
        response = await client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1200,
            reasoning_effort="low",
            response_format={"type": "json_object"},
        )
        raw_text = response.choices[0].message.content
        json_start = raw_text.find("{")
        json_end = raw_text.rfind("}") + 1
        if json_start == -1:
            return None
        result = json.loads(raw_text[json_start:json_end])
        return {
            **article,
            "summary": result.get("summary", ""),
            "key_points": result.get("key_points", []),
            "sentiment": result.get("sentiment", "neutral"),
            "category": result.get("category", "other"),
            "relevance_score": result.get("relevance_score", 0.5),
        }
    except Exception as e:
        print(f"Summarization failed for '{article['title'][:50]}...': {e}")
        return None
async def summarize_articles(articles: list[dict]) -> list[dict]:
    """Summarize a batch of articles, skipping any that fail."""
    summarized = []
    for article in articles:
        result = await summarize_article(article)
        if result is not None:
            summarized.append(result)
    print(f"Summarizer done → {len(summarized)}/{len(articles)} articles")
    return summarized