import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.llm_client.gemini_client import GeminiClient, LLMConfig
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
from graphiti_core.cross_encoder.gemini_reranker_client import GeminiRerankerClient
from dotenv import load_dotenv


load_dotenv()

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", None)
GEMINI_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not NEO4J_URI or not NEO4J_USER or not NEO4J_PASSWORD:
    raise ValueError(" You must set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD")

if not GEMINI_KEY:
    raise ValueError(" You must set GOOGLE_API_KEY in your environment to use Gemini")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("clients-graph")

# Helpers

def iso_timestamp_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

def ep(name: str, body: dict, description: str):
    return {
        "name": name,
        "body": json.dumps(body),
        "type": EpisodeType.json,
        "description": description,
    }

# Sample data (clients & interactions)

def create_client_episodes():
    episodes = []
    # ---- Clients (profils) ----
    for u, seg in [
        ("alice", "loyal"),
        ("bob", "new"),
        ("charlie", "bargain_hunter"),
        ("diana", "loyal"),
        ("eva", "influencer"),
    ]:
        episodes.append(ep(
            f"Signup {u}",
            {
                "type": "signup",
                "user": u,
                "segment": seg,
                "timestamp": iso_timestamp_days_ago(30),
            },
            f"{u} signed up 30 days ago",
        ))

    # ---- Vues produits ----
    views = [
        ("alice",   "p_sneakers",   "sportswear", 9),
        ("alice",   "p_watch",      "electronics", 8),
        ("bob",     "p_headphones", "electronics", 6),
        ("charlie", "p_blender",    "home", 5),
        ("diana",   "p_yoga_mat",   "sportswear", 7),
        ("eva",     "p_sneakers",   "sportswear", 4),
        ("eva",     "p_headphones", "electronics", 3),
    ]
    for u, p, c, d in views:
        episodes.append(ep(
            f"View {u} -> {p}",
            {
                "type": "view",
                "user": u,
                "product_id": p,
                "category": c,
                "timestamp": iso_timestamp_days_ago(d),
            },
            f"{u} viewed {p} ({c}) {d} days ago",
        ))

    # ---- Ajouts au panier ----
    carts = [
        ("alice",   "p_sneakers", "sportswear", 8),
        ("bob",     "p_headphones","electronics", 5),
        ("diana",   "p_yoga_mat", "sportswear", 6),
        ("eva",     "p_sneakers", "sportswear", 3),
    ]
    for u, p, c, d in carts:
        episodes.append(ep(
            f"AddToCart {u} -> {p}",
            {
                "type": "add_to_cart",
                "user": u,
                "product_id": p,
                "category": c,
                "timestamp": iso_timestamp_days_ago(d),
            },
            f"{u} added {p} to cart {d} days ago",
        ))

    # ---- Achats ----
    purchases = [
        ("alice",   "p_sneakers", "sportswear", 120.0, 7),
        ("charlie", "p_blender",  "home",        55.0, 4),
        ("diana",   "p_yoga_mat", "sportswear",  25.0, 5),
        ("eva",     "p_headphones","electronics",95.0, 2),
        ("eva",     "p_sneakers", "sportswear", 130.0, 1),
    ]
    for u, p, c, amount, d in purchases:
        episodes.append(ep(
            f"Purchase {u} -> {p}",
            {
                "type": "purchase",
                "user": u,
                "product_id": p,
                "category": c,
                "amount": amount,
                "currency": "USD",
                "timestamp": iso_timestamp_days_ago(d),
            },
            f"{u} purchased {p} ({amount} USD) {d} days ago",
        ))

    # ---- Avis ----
    reviews = [
        ("alice",  "p_sneakers", 5, "Great fit!", 6),
        ("charlie","p_blender",  4, "Good value", 3),
        ("eva",    "p_headphones",4, "Nice sound", 1),
    ]
    for u, p, stars, text, d in reviews:
        episodes.append(ep(
            f"Review {u} -> {p}",
            {
                "type": "review",
                "user": u,
                "product_id": p,
                "stars": stars,
                "text": text,
                "timestamp": iso_timestamp_days_ago(d),
            },
            f"{u} reviewed {p} ({stars}★) {d} days ago",
        ))

    # ---- Parrainages ----
    referrals = [
        ("eva", "bob",     10),
        ("eva", "charlie", 9),
        ("alice", "diana", 12),
    ]
    for src, dst, d in referrals:
        episodes.append(ep(
            f"Referral {src} -> {dst}",
            {
                "type": "referral",
                "referrer": src,
                "referred": dst,
                "timestamp": iso_timestamp_days_ago(d),
            },
            f"{src} referred {dst} {d} days ago",
        ))

    return episodes

# Natural-language queries exposing "graph characteristics"
async def q_top_connected_clients(graphiti: Graphiti, days: int = 30, k: int = 5):
    since_time = iso_timestamp_days_ago(days)
    query = f"top {k} clients by connectivity (referrals + interactions) since {since_time}"
    logger.info(f" Query (Top connected): {query}")
    return await graphiti.search(query=query)

async def q_high_intent_clients(graphiti: Graphiti, min_amount: float = 80.0, days: int = 14):
    since_time = iso_timestamp_days_ago(days)
    query = f"clients with purchases > {min_amount} or active carts since {since_time}"
    logger.info(f" Query (High intent): {query}")
    return await graphiti.search(query=query)

async def q_category_communities(graphiti: Graphiti, category: str = "sportswear", days: int = 30):
    since_time = iso_timestamp_days_ago(days)
    query = f"clients communities by shared interactions in category {category} since {since_time}"
    logger.info(f" Query (Communities): {query}")
    return await graphiti.search(query=query)

async def q_super_referrers(graphiti: Graphiti, min_referrals: int = 2, days: int = 30):
    since_time = iso_timestamp_days_ago(days)
    query = f"clients with referrals >= {min_referrals} since {since_time}"
    logger.info(f" Query (Super-referrers): {query}")
    return await graphiti.search(query=query)

# Main
async def main():
    # Initialisation avec Gemini
    graphiti = Graphiti(
        NEO4J_URI,
        NEO4J_USER,
        NEO4J_PASSWORD,
        llm_client=GeminiClient(
            config=LLMConfig(
                api_key=GEMINI_KEY,
                model="gemini-2.0-flash"
            )
        ),
        embedder=GeminiEmbedder(
            config=GeminiEmbedderConfig(
                api_key=GEMINI_KEY,
                embedding_model="embedding-001"
            )
        ),
        cross_encoder=GeminiRerankerClient(
            config=LLMConfig(
                api_key=GEMINI_KEY,
                model="gemini-2.5-flash-lite-preview-06-17"
            )
        )
    )

    try:
        await graphiti.build_indices_and_constraints()
        logger.info("✔ Indices and constraints built.")

        episodes = create_client_episodes()
        for e in episodes:
            await graphiti.add_episode(
                name=e["name"],
                episode_body=e["body"],
                source=e["type"],
                source_description=e["description"],
                reference_time=datetime.now(timezone.utc),
            )
            logger.info(f"✔ Added episode: {e['name']}")
            await asyncio.sleep(10) 

        top_connected = await q_top_connected_clients(graphiti, days=30, k=5)
        print("\n--- Top Connected Clients (last 30 days) ---")
        for r in top_connected:
            print(f" UUID: {r.uuid} | Fact: {r.fact} | Time: {r.valid_at or r.ingested_at}")

        high_intent = await q_high_intent_clients(graphiti, min_amount=80.0, days=14)
        print("\n--- High-Intent Clients (purchases > 80 USD OR active carts, last 14 days) ---")
        for r in high_intent:
            print(f" UUID: {r.uuid} | Fact: {r.fact} | Time: {r.valid_at or r.ingested_at}")

        sportswear_comms = await q_category_communities(graphiti, category="sportswear", days=30)
        print("\n--- Communities around 'sportswear' (last 30 days) ---")
        for r in sportswear_comms:
            print(f" UUID: {r.uuid} | Fact: {r.fact} | Time: {r.valid_at or r.ingested_at}")

        super_ref = await q_super_referrers(graphiti, min_referrals=2, days=30)
        print("\n--- Super-Referrers (>=2 referrals, last 30 days) ---")
        for r in super_ref:
            print(f" UUID: {r.uuid} | Fact: {r.fact} | Time: {r.valid_at or r.ingested_at}")

    finally:
        await graphiti.close()
        logger.info("✔ Graphiti connection closed.")

if __name__ == "__main__":
    asyncio.run(main())
