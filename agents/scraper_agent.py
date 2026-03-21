import asyncio
import uuid
import json
from datetime import datetime
from playwright.async_api import async_playwright

async def scrape_hackernews():
    articles = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Opening HackerNews...")
        await page.goto("https://news.ycombinator.com", timeout=15000)
        await page.wait_for_selector(".athing", timeout=8000)
        rows = await page.query_selector_all(".athing")
        print(f"Found {len(rows)} articles")
        for row in rows[:20]:
            try:
                title_el = await row.query_selector(".titleline > a")
                if not title_el:
                    continue
                title = await title_el.inner_text()
                url   = await title_el.get_attribute("href")
                if not url.startswith("http"):
                    url = f"https://news.ycombinator.com/{url}"
                articles.append({
                    "id":           str(uuid.uuid4()),
                    "title":        title.strip(),
                    "url":          url,
                    "source":       "hackernews",
                    "raw_content":  title.strip(),
                    "score":        0,
                    "published_at": datetime.utcnow().isoformat()
                })
            except:
                continue
        await browser.close()
    return articles

async def scrape_devto():
    articles = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print("Opening dev.to...")
            await page.goto(
                "https://dev.to/t/ai", 
                timeout=30000,
                wait_until="domcontentloaded"
            )
            
            await page.wait_for_selector(".crayons-story", timeout=20000)
            
            posts = await page.query_selector_all(".crayons-story")
            print(f"Found {len(posts)} posts")
            
            for post in posts[:20]:
                try:
                    title_el = await post.query_selector("h2 a")
                    if not title_el:
                        continue
                    title = await title_el.inner_text()
                    url   = await title_el.get_attribute("href")
                    if not url.startswith("http"):
                        url = f"https://dev.to{url}"
                    articles.append({
                        "id":           str(uuid.uuid4()),
                        "title":        title.strip(),
                        "url":          url,
                        "source":       "devto",
                        "raw_content":  title.strip(),
                        "score":        0,
                        "published_at": datetime.utcnow().isoformat()
                    })
                except:
                    continue
                    
            print(f"dev.to: {len(articles)} articles")
            
        except Exception as e:
            print(f"dev.to failed: {e}")
            
        await browser.close()
    return articles
async def run_all_scrapers():
    print("Starting scrapers...")
    
    hn_articles    = await scrape_hackernews()
    print(f"HackerNews: {len(hn_articles)} articles")
    
    devto_articles = await scrape_devto()
    print(f"Dev.to: {len(devto_articles)} articles")
    
    all_articles = hn_articles + devto_articles
    print(f"Total: {len(all_articles)} articles")
    
    return all_articles

if __name__ == "__main__":
    articles = asyncio.run(run_all_scrapers())
    # Save to JSON file so notebook can read it
    with open("scraped_articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(articles)} articles to scraped_articles.json")
    for a in articles[:3]:
        print(f"  -> {a['title'][:60]}")
        print(f"     {a['source']} | {a['url'][:50]}")