from __future__ import annotations

import json
from typing import Any

import pytest


class _FakeS3:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_object(
        self,
        key: str,
        body: bytes | str,
        content_type: str = "application/json",
    ) -> str:
        payload = body.encode("utf-8") if isinstance(body, str) else body
        self.objects[key] = payload
        return f"s3://portfolio-exports/{key}"

    def get_object(self, key: str) -> bytes:
        return self.objects[key]

    def list_objects(self, prefix: str) -> list[str]:
        return [k for k in self.objects if k.startswith(prefix)]


@pytest.fixture
def fake_s3(client: Any) -> _FakeS3:  # noqa: ARG001 — ensures app TestClient is active
    from app.main import app
    from app.services.s3_service import get_s3_service

    service = _FakeS3()
    get_s3_service.cache_clear()
    app.dependency_overrides[get_s3_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_s3_service, None)
    get_s3_service.cache_clear()


@pytest.mark.integration
def test_export_uploads_json_to_localstack(client: Any, fake_s3: _FakeS3) -> None:
    create = client.post(
        "/portfolios",
        json={"name": "export-test", "currency": "USD"},
    )
    assert create.status_code == 201
    portfolio_id = create.json()["id"]

    client.post(
        f"/portfolios/{portfolio_id}/trades",
        json={
            "ticker": "AAPL",
            "trade_type": "BUY",
            "quantity": 5,
            "price": 100,
        },
    )

    response = client.post(f"/portfolios/{portfolio_id}/export")
    assert response.status_code == 200
    data = response.json()
    assert data["s3_uri"].startswith("s3://")
    assert data["trade_count"] >= 1
    assert data["size_bytes"] > 0

    keys = list(fake_s3.objects.keys())
    assert any(k.startswith(f"portfolio-{portfolio_id}/") for k in keys)
    stored = json.loads(next(iter(fake_s3.objects.values())).decode("utf-8"))
    assert stored["portfolio_id"] == portfolio_id
    assert len(stored["trades"]) >= 1


@pytest.mark.integration
def test_export_404_for_missing_portfolio(client: Any, fake_s3: _FakeS3) -> None:
    response = client.post("/portfolios/999999/export")
    assert response.status_code == 404
    assert fake_s3.objects == {}
