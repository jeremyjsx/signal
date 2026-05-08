import logging
import re
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug[:80] or "untitled"


def write_curated_article_to_obsidian(
    article_id: int,
    title: str,
    url: str,
    score: float,
    summary: Optional[str],
    published_at: Optional[str],
    feed_name: str,
) -> Optional[str]:
    """Write curated article as markdown file in Obsidian vault."""
    vault_path_value = settings.obsidian_vault_path.strip()
    if not vault_path_value:
        return None

    vault_path = Path(vault_path_value).expanduser()
    if not vault_path.exists() or not vault_path.is_dir():
        logger.warning("Obsidian vault path not found: %s", vault_path)
        return None

    curated_dir = vault_path / "Signal Curated"
    curated_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{article_id}-{_slugify(title)}.md"
    file_path = curated_dir / filename

    markdown = (
        f"# {title}\n\n"
        f"- Source: {feed_name}\n"
        f"- URL: {url}\n"
        f"- AI Score: {score:.2f}\n"
        f"- Published At: {published_at or 'unknown'}\n\n"
        "## Summary\n\n"
        f"{summary or 'No summary available.'}\n"
    )

    file_path.write_text(markdown, encoding="utf-8")
    return str(file_path)
