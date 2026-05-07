from groq import AsyncGroq

from app.core.config import settings


async def analyze_articles_batch(articles: list) -> list:
    """Analyze multiple articles in one AI call"""
    if not settings.groq_api_key:
        return [0.0] * len(articles)
    
    if not articles:
        return []

    client = AsyncGroq(api_key=settings.groq_api_key)
    
    articles_text = "\n".join([
        f"{i+1}. {title[:80]} - {summary[:80] if summary else ''}"
        for i, (title, summary) in enumerate(articles)
    ])
    
    prompt = f"""Analyze these articles and give a relevance score (0-1) for a software engineer interested in:
- System design, Backend architecture, Infrastructure, DevOps, New technologies

Articles:
{articles_text}

Respond ONLY with {len(articles)} numbers between 0 and 1, one per line. No other text."""

    try:
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        
        msg = response.choices[0].message
        if not msg or not msg.content:
            return [0.0] * len(articles)
        
        scores = []
        for line in msg.content.strip().split("\n"):
            try:
                scores.append(float(line.strip()))
            except (ValueError, TypeError):
                scores.append(0.0)
        
        return scores[:len(articles)]
    except Exception:
        return [0.0] * len(articles)