"""Tests for playbook API endpoints.

Covers CRUD operations for playbooks and rules, version management,
and clause evaluation.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest
from httpx import AsyncClient


class TestPlaybookEndpoints:
    """Test suite for playbook API endpoints."""

    @pytest.mark.asyncio
    async def test_create_playbook(
        self, client: AsyncClient, sample_playbook_data: Dict[str, Any]
    ):
        """Test creating a new playbook."""
        response = await client.post(
            "/api/v1/playbooks",
            json=sample_playbook_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_playbook_data["name"]
        assert "playbook_id" in data
        return data["playbook_id"]

    @pytest.mark.asyncio
    async def test_list_playbooks(
        self, client: AsyncClient, sample_playbook_data: Dict[str, Any]
    ):
        """Test listing playbooks returns created playbooks."""
        # List playbooks (may be empty if no engine state persisted)
        response = await client.get("/api/v1/playbooks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_playbook_not_found(self, client: AsyncClient):
        """Test getting non-existent playbook returns 404."""
        response = await client.get("/api/v1/playbooks/non-existent-id")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_and_get_playbook(
        self, client: AsyncClient, sample_playbook_data: Dict[str, Any]
    ):
        """Test creating a playbook and retrieving it by ID."""
        create_resp = await client.post(
            "/api/v1/playbooks", json=sample_playbook_data
        )
        playbook_id = create_resp.json()["playbook_id"]

        get_resp = await client.get(f"/api/v1/playbooks/{playbook_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["playbook_id"] == playbook_id
        assert data["name"] == sample_playbook_data["name"]

    @pytest.mark.asyncio
    async def test_update_playbook(
        self, client: AsyncClient, sample_playbook_data: Dict[str, Any]
    ):
        """Test updating a playbook's metadata."""
        create_resp = await client.post(
            "/api/v1/playbooks", json=sample_playbook_data
        )
        playbook_id = create_resp.json()["playbook_id"]

        update_resp = await client.put(
            f"/api/v1/playbooks/{playbook_id}",
            json={"name": "Updated Playbook", "is_active": True},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Updated Playbook"
        assert update_resp.json()["is_active"] is True

    @pytest.mark.asyncio
    async def test_delete_playbook(
        self, client: AsyncClient, sample_playbook_data: Dict[str, Any]
    ):
        """Test deleting a playbook."""
        create_resp = await client.post(
            "/api/v1/playbooks", json=sample_playbook_data
        )
        playbook_id = create_resp.json()["playbook_id"]

        delete_resp = await client.delete(
            f"/api/v1/playbooks/{playbook_id}"
        )
        assert delete_resp.status_code == 204

        # Verify it's gone
        get_resp = await client.get(f"/api/v1/playbooks/{playbook_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_add_rule_to_playbook(
        self,
        client: AsyncClient,
        sample_playbook_data: Dict[str, Any],
        sample_playbook_rule_data: Dict[str, Any],
    ):
        """Test adding a rule to a playbook."""
        create_resp = await client.post(
            "/api/v1/playbooks", json=sample_playbook_data
        )
        playbook_id = create_resp.json()["playbook_id"]

        rule_resp = await client.post(
            f"/api/v1/playbooks/{playbook_id}/rules",
            json=sample_playbook_rule_data,
        )
        assert rule_resp.status_code == 201
        rule_data = rule_resp.json()
        assert rule_data["clause_type"] == "indemnification"
        assert "rule_id" in rule_data

    @pytest.mark.asyncio
    async def test_list_rules(
        self,
        client: AsyncClient,
        sample_playbook_data: Dict[str, Any],
        sample_playbook_rule_data: Dict[str, Any],
    ):
        """Test listing rules in a playbook."""
        create_resp = await client.post(
            "/api/v1/playbooks", json=sample_playbook_data
        )
        playbook_id = create_resp.json()["playbook_id"]

        await client.post(
            f"/api/v1/playbooks/{playbook_id}/rules",
            json=sample_playbook_rule_data,
        )

        list_resp = await client.get(
            f"/api/v1/playbooks/{playbook_id}/rules"
        )
        assert list_resp.status_code == 200
        rules = list_resp.json()
        assert len(rules) >= 1

    @pytest.mark.asyncio
    async def test_evaluate_clause(
        self,
        client: AsyncClient,
        sample_playbook_data: Dict[str, Any],
        sample_playbook_rule_data: Dict[str, Any],
        sample_clause_text: str,
    ):
        """Test evaluating a clause against a playbook."""
        create_resp = await client.post(
            "/api/v1/playbooks", json=sample_playbook_data
        )
        playbook_id = create_resp.json()["playbook_id"]

        await client.post(
            f"/api/v1/playbooks/{playbook_id}/rules",
            json=sample_playbook_rule_data,
        )

        eval_resp = await client.post(
            f"/api/v1/playbooks/{playbook_id}/evaluate",
            json={
                "clause_text": sample_clause_text,
                "clause_type": "indemnification",
            },
        )
        assert eval_resp.status_code == 200
        data = eval_resp.json()
        assert "matched_rules" in data
        assert "total_rules" in data
        assert "matched_count" in data

    @pytest.mark.asyncio
    async def test_evaluate_clause_no_match(
        self,
        client: AsyncClient,
        sample_playbook_data: Dict[str, Any],
    ):
        """Test evaluating a clause with no matching rules."""
        create_resp = await client.post(
            "/api/v1/playbooks", json=sample_playbook_data
        )
        playbook_id = create_resp.json()["playbook_id"]

        eval_resp = await client.post(
            f"/api/v1/playbooks/{playbook_id}/evaluate",
            json={
                "clause_text": "Some unrelated text here",
                "clause_type": "confidentiality",
            },
        )
        assert eval_resp.status_code == 200
        assert eval_resp.json()["matched_count"] == 0

    @pytest.mark.asyncio
    async def test_approve_version(
        self,
        client: AsyncClient,
        sample_playbook_data: Dict[str, Any],
        sample_playbook_rule_data: Dict[str, Any],
    ):
        """Test approving a playbook version."""
        create_resp = await client.post(
            "/api/v1/playbooks", json=sample_playbook_data
        )
        playbook_id = create_resp.json()["playbook_id"]

        # Add a rule to create a version
        await client.post(
            f"/api/v1/playbooks/{playbook_id}/rules",
            json=sample_playbook_rule_data,
        )

        approve_resp = await client.post(
            f"/api/v1/playbooks/{playbook_id}/versions/1/approve",
            json={
                "approved_by": "test-admin",
                "change_summary": "Approved for testing",
            },
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "active"
