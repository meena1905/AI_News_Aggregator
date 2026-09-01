
from typing import TypedDict
from langgraph.graph import StateGraph, END

from agents.scraper_agent import scrape_articles
from agents.summarizer_agent import summarize_articles
from agents.personalizer_agent import personalize_articles
from agents.emailer_agent import send_digests
from db.queries import save_articles


class PipelineState(TypedDict, total=False):
    articles: list[dict]
    summarized: list[dict]
    personalized: dict
    emails_sent: list[str]
    target_user_id: str | None


async def scrape_node(state: PipelineState) -> PipelineState:
    articles = await scrape_articles()
    return {"articles": articles}


async def summarize_node(state: PipelineState) -> PipelineState:
    summarized = await summarize_articles(state["articles"])
    if summarized:
        await save_articles(summarized)
    return {"summarized": summarized}
async def personalize_node(state: PipelineState) -> PipelineState:
    personalized = await personalize_articles(state["summarized"], user_id=state.get("target_user_id"))
    return {"personalized": personalized}
async def email_node(state: PipelineState) -> PipelineState:
    emails_sent = await send_digests(state["personalized"])
    return {"emails_sent": emails_sent}
def build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("scrape", scrape_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("personalize", personalize_node)
    graph.add_node("email", email_node)
    graph.set_entry_point("scrape")
    graph.add_edge("scrape", "summarize")
    graph.add_edge("summarize", "personalize")
    graph.add_edge("personalize", "email")
    graph.add_edge("email", END)
    return graph.compile()

async def run_pipeline(user_id: str | None = None) -> PipelineState:
    app = build_graph()
    result = await app.ainvoke({"target_user_id": user_id})
    print(f"✅ Pipeline complete → {len(result.get('emails_sent', []))} digests sent")
    return result