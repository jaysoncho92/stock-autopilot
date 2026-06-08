from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Market, MarketReport, Opinion, StockAnalysis


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_trigger_job_mocked(client):
    mock_report = MarketReport(
        generated_at="2025-01-01T00:00:00+00:00",
        analyses=[
            StockAnalysis(
                symbol="AAPL",
                name="Apple",
                market=Market.US,
                last_close=190.0,
                change_1d_pct=1.0,
                change_5d_pct=2.0,
                ma5=188.0,
                ma20=185.0,
                rsi14=55.0,
                opinion=Opinion.HOLD,
                rationale="测试",
            )
        ],
        summary="测试摘要",
    )
    with patch("app.main.run_market_report_job", new=AsyncMock(return_value=mock_report)):
        response = client.post("/jobs/run")
    assert response.status_code == 200
    assert response.json()["summary"] == "测试摘要"
