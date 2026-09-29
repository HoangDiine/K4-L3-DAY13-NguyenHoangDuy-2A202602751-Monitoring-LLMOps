from __future__ import annotations

import json
import asyncio
from pathlib import Path

import httpx

from app import logging_config
from app.main import app


def test_chat_response_log_exposes_quality_for_dashboard(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(
                "/chat",
                json={
                    "user_id": "student-01",
                    "session_id": "session-01",
                    "feature": "qa",
                    "message": "Explain observability",
                },
            )

    response = asyncio.run(send_request())

    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert "x-response-time-ms" in response.headers
    assert response.headers["x-request-id"] == response.json()["correlation_id"]

    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    response_event = next(event for event in events if event["event"] == "response_sent")
    assert response_event["quality_score"] == response.json()["quality_score"]
    assert response_event["ttft_ms"] == response.json()["ttft_ms"]
    assert response_event["tool_name"] == "retrieval"
    assert response_event["tool_success"] is True
    assert "correlation_id" in response_event
    assert "user_id_hash" in response_event
    assert "session_id" in response_event
    assert "feature" in response_event
    assert "model" in response_event


def test_custom_correlation_id_and_pii_scrubbing(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    custom_id = "req-custom01"

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(
                "/chat",
                headers={"x-request-id": custom_id},
                json={
                    "user_id": "student-42",
                    "session_id": "session-42",
                    "feature": "qa",
                    "message": "Mail secret@test.com, card 4111 2222 3333 4444",
                },
            )

    response = asyncio.run(send_request())
    assert response.status_code == 200
    assert response.headers["x-request-id"] == custom_id
    assert response.json()["correlation_id"] == custom_id

    log_content = log_path.read_text(encoding="utf-8")
    assert "secret@test.com" not in log_content
    assert "4111 2222 3333 4444" not in log_content
    assert "[REDACTED_EMAIL]" in log_content
    assert "[REDACTED_CREDIT_CARD]" in log_content

