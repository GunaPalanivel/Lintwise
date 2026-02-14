"""Tests for lintwise.api — endpoints, schemas, middleware."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from lintwise.api.app import create_app
from lintwise.api.schemas import (
    ErrorResponse,
    HealthResponse,
    ManualReviewRequest,
    ReviewCommentResponse,
    ReviewRequest,
    ReviewResponse,
)


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ── Schemas ─────────────────────────────────────────────────────────────────


class TestAPISchemas:
    def test_review_request(self):
        r = ReviewRequest(pr_url="https://github.com/org/repo/pull/1")
        assert r.pr_url == "https://github.com/org/repo/pull/1"

    def test_manual_review_request(self):
        r = ManualReviewRequest(diff_text="@@ -1,3 +1,4 @@\n+new line")
        assert len(r.diff_text) > 10
        assert r.title == "Manual Review"

    def test_manual_review_too_short(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ManualReviewRequest(diff_text="short")

    def test_review_response_defaults(self):
        r = ReviewResponse()
        assert r.status == "completed"
        assert r.risk_score == "low"
        assert r.total_comments == 0
        assert r.comments == []

    def test_review_comment_response(self):
        c = ReviewCommentResponse(
            file="main.py",
            line=42,
            severity="critical",
            category="security",
            title="SQL injection",
            body="User input in query.",
            confidence=0.95,
        )
        assert c.severity == "critical"
        assert c.confidence == 0.95

    def test_health_response(self):
        h = HealthResponse()
        assert h.status == "healthy"
        assert h.version == "0.1.0"

    def test_error_response(self):
        e = ErrorResponse(error="Not Found", detail="PR not found")
        assert e.error == "Not Found"


# ── Health Endpoints ────────────────────────────────────────────────────────


class TestHealthEndpoints:
    def test_health(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_readiness(self, client):
        response = client.get("/api/v1/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_root_redirects(self, client):
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307


# ── Review Endpoints ────────────────────────────────────────────────────────


class TestReviewEndpoints:
    def test_review_no_service(self, client):
        """Without configured services, returns 503."""
        response = client.post(
            "/api/v1/reviews/",
            json={"pr_url": "https://github.com/org/repo/pull/1"},
        )
        assert response.status_code == 503

    def test_manual_review_no_service(self, client):
        response = client.post(
            "/api/v1/reviews/manual",
            json={"diff_text": "@@ -1,3 +1,4 @@\n+new line addition here"},
        )
        assert response.status_code == 503


# ── Webhook Endpoint ────────────────────────────────────────────────────────


class TestWebhookEndpoint:
    def test_invalid_json(self, client):
        response = client.post(
            "/api/v1/webhooks/github",
            content=b"not json",
            headers={"X-GitHub-Event": "pull_request"},
        )
        assert response.status_code == 400

    def test_non_actionable_event(self, client):
        payload = {"action": "created", "issue": {"number": 1}}
        response = client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "issues"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "ignored"

    def test_pr_opened_event(self, client):
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "Test",
                "head": {"ref": "f", "sha": "a"},
                "base": {"ref": "m", "sha": "b"},
            },
            "repository": {"full_name": "org/repo", "name": "repo"},
            "sender": {"login": "user"},
        }
        response = client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "pull_request"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["action"] == "opened"


# ── OpenAPI Docs ────────────────────────────────────────────────────────────


class TestDocs:
    def test_openapi_available(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "Lintwise"

    def test_docs_page(self, client):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_request_id_header(self, client):
        response = client.get("/api/v1/health")
        assert "x-request-id" in response.headers
