import json
from db.queries import get_users
TOP_N_ARTICLES = 10
TITLE_MATCH_BOOST = 0.3
SUMMARY_MATCH_BOOST = 0.2
def _score_article(article: dict, interests_lower: list[str]) -> float:
    score = float(article.get("relevance_score") or 0.5)
    title = article["title"].lower()
    summary = (article.get("summary") or "").lower()
    for interest in interests_lower:
        if interest in title:
            score += TITLE_MATCH_BOOST
        if interest in summary:
            score += SUMMARY_MATCH_BOOST
    return score
async def personalize_articles(articles: list[dict], user_id: str | None = None) -> dict:
    """
    Returns { user_id: { "user": {...}, "articles": [top N scored articles] } }
    for every user in the users table — or just the one user_id given,
    when this run was triggered by a single person clicking "Send My
    Digest Now" rather than the scheduled daily run for everyone.
    """
    users = await get_users(user_id=user_id)
    personalized = {}

    for user in users:
        interests = user["interests"]
        if isinstance(interests, str):
            interests = json.loads(interests)
        interests_lower = [i.lower() for i in interests]

        scored = [
            {**article, "personal_score": _score_article(article, interests_lower)}
            for article in articles
        ]
        scored.sort(key=lambda a: a["personal_score"], reverse=True)

        personalized[user["user_id"]] = {
            "user": user,
            "articles": scored[:TOP_N_ARTICLES],
        }

    print(f"✅ Personalizer done → {len(personalized)} users")
    return personalized