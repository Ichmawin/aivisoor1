import asyncio
import httpx
import json
import re
from openai import AsyncOpenAI
from config import settings
import logging

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


# ── Query Generator ───────────────────────────────────────────────────────────

def generate_queries(domain: str, niche: str | None = None) -> list[str]:
    """Generate diverse queries to check AI visibility for a domain."""
    base = niche or domain.replace("www.", "").split(".")[0]
    return [
        f"What is {base}?",
        f"Best tools for {base}",
        f"How does {base} work?",
        f"Alternatives to {base}",
        f"Is {base} worth using?",
        f"Review of {base}",
        f"{base} vs competitors",
        f"Who uses {base}?",
    ]


# ── OpenAI Provider ───────────────────────────────────────────────────────────

async def query_openai(query: str) -> dict:
    try:
        response = await openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": query}],
            max_tokens=800,
            temperature=0.3,
        )
        return {
            "provider": "openai",
            "query": query,
            "answer": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens,
        }
    except Exception as e:
        logger.error(f"OpenAI query failed: {e}")
        return {"provider": "openai", "query": query, "answer": "", "error": str(e)}


# ── Perplexity Provider ───────────────────────────────────────────────────────

async def query_perplexity(query: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}"},
                json={
                    "model": settings.PERPLEXITY_MODEL,
                    "messages": [{"role": "user", "content": query}],
                    "max_tokens": 800,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "provider": "perplexity",
                "query": query,
                "answer": data["choices"][0]["message"]["content"],
                "citations": data.get("citations", []),
            }
    except Exception as e:
        logger.error(f"Perplexity query failed: {e}")
        return {"provider": "perplexity", "query": query, "answer": "", "error": str(e)}


# ── Answer Parser & Scorer ────────────────────────────────────────────────────

def parse_answer(answer: str, domain: str) -> dict:
    """Extract mentions, sentiment, position from an AI answer."""
    domain_clean = domain.replace("www.", "").lower()
    name = domain_clean.split(".")[0]

    answer_lower = answer.lower()
    mentioned = domain_clean in answer_lower or name in answer_lower

    # Find position (which sentence mentions domain)
    sentences = [s.strip() for s in re.split(r"[.!?]", answer) if s.strip()]
    mention_position = None
    for i, sent in enumerate(sentences):
        if name in sent.lower() or domain_clean in sent.lower():
            mention_position = i + 1
            break

    # Sentiment around mention
    sentiment = "neutral"
    positive_words = ["best", "great", "excellent", "recommend", "top", "leading", "popular"]
    negative_words = ["avoid", "poor", "bad", "worst", "not recommend", "issues"]
    context = answer_lower
    if any(w in context for w in positive_words):
        sentiment = "positive"
    elif any(w in context for w in negative_words):
        sentiment = "negative"

    # Extract competitors mentioned
    competitors = extract_entities(answer, exclude=domain_clean)

    return {
        "mentioned": mentioned,
        "mention_position": mention_position,
        "total_sentences": len(sentences),
        "sentiment": sentiment,
        "competitors_mentioned": competitors[:5],
    }


def extract_entities(text: str, exclude: str = "") -> list[str]:
    """Basic entity extraction — company/brand names."""
    # Match capitalized words that look like brand names
    pattern = r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)?\b"
    candidates = re.findall(pattern, text)
    # Filter common words and the domain itself
    stop = {"The", "This", "That", "These", "With", "From", "When", "Where", "What", "How"}
    return [c for c in candidates if c not in stop and exclude not in c.lower()]


def calculate_scores(results: list[dict], domain: str) -> dict:
    """
    Calculate three core scores:
    - AI Visibility Score: how often domain is mentioned
    - Authority Score: sentiment + position quality
    - Coverage Score: breadth across query types
    """
    if not results:
        return {"visibility": 0, "authority": 0, "coverage": 0, "overall": 0}

    total = len(results)
    mentions = sum(1 for r in results if r.get("mentioned"))

    # Visibility: % of queries that mention the domain
    visibility = round((mentions / total) * 100)

    # Authority: based on position and sentiment
    authority_scores = []
    for r in results:
        if not r.get("mentioned"):
            continue
        pos = r.get("mention_position", 999)
        total_sents = r.get("total_sentences", 10) or 10
        position_score = max(0, 1 - (pos - 1) / total_sents) * 100

        sentiment_bonus = {"positive": 20, "neutral": 0, "negative": -20}.get(
            r.get("sentiment", "neutral"), 0
        )
        authority_scores.append(min(100, max(0, position_score + sentiment_bonus)))

    authority = round(sum(authority_scores) / len(authority_scores)) if authority_scores else 0

    # Coverage: unique providers and query types covered
    providers_used = len(set(r.get("provider") for r in results if r.get("mentioned")))
    coverage = round((mentions / total) * 70 + (providers_used / 2) * 30)
    coverage = min(100, coverage)

    overall = round(visibility * 0.4 + authority * 0.35 + coverage * 0.25)

    return {
        "visibility": visibility,
        "authority": authority,
        "coverage": coverage,
        "overall": overall,
    }


# ── Main Analysis Runner ──────────────────────────────────────────────────────

async def run_ai_analysis(domain: str, niche: str | None = None) -> dict:
    """Run full AI visibility analysis for a domain."""
    queries = generate_queries(domain, niche)

    # Run all queries in parallel across both providers
    tasks = []
    for q in queries:
        tasks.append(query_openai(q))
        tasks.append(query_perplexity(q))

    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Parse each result
    parsed_results = []
    for r in raw_results:
        if isinstance(r, Exception):
            continue
        if r.get("answer"):
            parsed = parse_answer(r["answer"], domain)
            parsed_results.append({**r, **parsed})

    scores = calculate_scores(parsed_results, domain)

    # Aggregate competitors
    all_competitors: dict[str, int] = {}
    for r in parsed_results:
        for comp in r.get("competitors_mentioned", []):
            all_competitors[comp] = all_competitors.get(comp, 0) + 1

    top_competitors = sorted(all_competitors.items(), key=lambda x: -x[1])[:10]

    return {
        "domain": domain,
        "scores": scores,
        "queries_run": len(queries),
        "total_responses": len(parsed_results),
        "mention_count": sum(1 for r in parsed_results if r.get("mentioned")),
        "top_competitors": [{"name": c, "mentions": m} for c, m in top_competitors],
        "raw_results": parsed_results,
    }
