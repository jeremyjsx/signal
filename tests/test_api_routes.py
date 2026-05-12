from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.main import create_app
from app.modules.articles import routes as article_routes
from app.modules.feeds import routes as feed_routes


class DummyDb:
    pass


def _create_test_client():
    app = create_app()

    async def override_get_db():
        yield DummyDb()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_feeds_quality_endpoint_passes_filters(monkeypatch):
    captured = {}

    async def fake_list_feed_quality_db(
        db, status=None, min_scored_articles=None, min_curated_rate=None
    ):
        captured["status"] = status
        captured["min_scored_articles"] = min_scored_articles
        captured["min_curated_rate"] = min_curated_rate
        return {"items": [{"feed_id": 1, "health_status": "degraded"}]}

    monkeypatch.setattr(feed_routes, "list_feed_quality_db", fake_list_feed_quality_db)

    original_api_key = settings.api_key
    settings.api_key = "test-key"
    try:
        with _create_test_client() as client:
            response = client.get(
                "/api/feeds/quality?status=degraded&min_scored_articles=5&min_curated_rate=0.2",
                headers={"X-API-Key": "test-key"},
            )
    finally:
        settings.api_key = original_api_key

    assert response.status_code == 200
    assert response.json()["items"][0]["health_status"] == "degraded"
    assert captured == {
        "status": "degraded",
        "min_scored_articles": 5,
        "min_curated_rate": 0.2,
    }


def test_retry_failed_obsidian_endpoint_calls_service(monkeypatch):
    captured = {}

    async def fake_retry_failed_obsidian_exports_db(limit, db):
        captured["limit"] = limit
        return {"retried": 2, "article_ids": [10, 11]}

    monkeypatch.setattr(
        article_routes,
        "retry_failed_obsidian_exports_db",
        fake_retry_failed_obsidian_exports_db,
    )

    original_api_key = settings.api_key
    settings.api_key = "test-key"
    try:
        with _create_test_client() as client:
            response = client.post(
                "/api/articles/obsidian/retry-failed?limit=25",
                headers={"X-API-Key": "test-key"},
            )
    finally:
        settings.api_key = original_api_key

    assert response.status_code == 200
    assert response.json() == {"retried": 2, "article_ids": [10, 11]}
    assert captured["limit"] == 25
