import asyncio
import uuid
import json
from datetime import datetime
from playwright.sync_api import sync_playwright
ARTICLES_PER_SOURCE = 60
def _scrape_hackernews_sync(limit: int = ARTICLES_PER_SOURCE) -> list[dict]:
    articles = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        print("Opening HackerNews...")
        page.goto("https://news.ycombinator.com", timeout=15000)
        page.wait_for_selector(".athing", timeout=8000)
        rows = page.query_selector_all(".athing")
        print(f"Found {len(rows)} articles")
        for row in rows[:limit]:
            try:
                title_el = row.query_selector(".titleline > a")
                if not title_el:
                    continue
                title = title_el.inner_text()
                url = title_el.get_attribute("href")
                if not url.startswith("http"):
                    url = f"https://news.ycombinator.com/{url}"
                articles.append({
                    "id": str(uuid.uuid4()),
                    "title": title.strip(),
                    "url": url,
                    "source": "hackernews",
                    "raw_content": title.strip(),
                    "score": 0,
                    "published_at": datetime.utcnow().isoformat(),
                })
            except Exception:
                continue
        browser.close()
    return articles
def _scrape_devto_sync(limit: int = ARTICLES_PER_SOURCE) -> list[dict]:
    articles = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            print("Opening dev.to...")
            page.goto("https://dev.to/t/ai", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_selector(".crayons-story", timeout=20000)
            posts = page.query_selector_all(".crayons-story")
            print(f"Found {len(posts)} posts")
            for post in posts[:limit]:
                try:
                    title_el = post.query_selector("h2 a")
                    if not title_el:
                        continue
                    title = title_el.inner_text()
                    url = title_el.get_attribute("href")
                    if not url.startswith("http"):
                        url = f"https://dev.to{url}"
                    articles.append({
                        "id": str(uuid.uuid4()),
                        "title": title.strip(),
                        "url": url,
                        "source": "devto",
                        "raw_content": title.strip(),
                        "score": 0,
                        "published_at": datetime.utcnow().isoformat(),
                    })
                except Exception:
                    continue
            print(f"dev.to: {len(articles)} articles")
        except Exception as e:
            print(f"dev.to failed: {e}")
        browser.close()
    return articles
def _scrape_all_sync() -> list[dict]:
    """Runs both sync scrapers back-to-back in the worker thread."""
    print("Starting scrapers...")
    hn_articles = _scrape_hackernews_sync()
    print(f"HackerNews: {len(hn_articles)} articles")
    devto_articles = _scrape_devto_sync()
    print(f"Dev.to: {len(devto_articles)} articles")
    all_articles = hn_articles + devto_articles
    seen = set()
    deduped = []
    for a in all_articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            deduped.append(a)
    print(f"Total: {len(deduped)} articles (after dedup)")
    return deduped
async def scrape_articles() -> list[dict]:
    """
    Main entrypoint used by the LangGraph workflow. Runs the sync
    scrapers in a background thread (see module docstring for why) and
    returns a combined, deduplicated list.
    """
    return await asyncio.to_thread(_scrape_all_sync)
if __name__ == "__main__":
    articles = asyncio.run(scrape_articles())
    with open("scraped_articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(articles)} articles to scraped_articles.json")
    for a in articles[:3]:
        print(f"  -> {a['title'][:60]}")
        print(f"     {a['source']} | {a['url'][:50]}")