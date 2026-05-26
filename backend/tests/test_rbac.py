"""RBAC authorization tests — validates role-based permission enforcement.

Tests:
  - Role-to-permission resolution
  - can() policy check with tenant isolation
  - can() policy check with ownership validation
  - Permission boundaries between roles
"""

from __future__ import annotations

import pytest
from app.kernel.security.roles import Roles, can, resolve_permissions, Actions
from app.kernel.security.auth import UserContext
from tests.conftest import TENANT_A_ID_STR, TENANT_B_ID_STR


class TestRoleResolution:
    """Server-side role-to-permission resolution."""

    def test_admin_has_full_permissions(self, rbac_admin_user):
        """Admin should have all permissions."""
        assert "contracts:read" in rbac_admin_user.permissions
        assert "contracts:write" in rbac_admin_user.permissions
        assert "contracts:approve" in rbac_admin_user.permissions
        assert "audit:read" in rbac_admin_user.permissions
        assert "admin:tenant" in rbac_admin_user.permissions
        assert "reviews:export" in rbac_admin_user.permissions

    def test_viewer_has_limited_permissions(self, viewer_user):
        """Viewer should only have read permissions."""
        assert "contracts:read" in viewer_user.permissions
        assert "contracts:write" not in viewer_user.permissions
        assert "contracts:approve" not in viewer_user.permissions
        assert "audit:read" in viewer_user.permissions
        assert "workflows:write" not in viewer_user.permissions

    def test_legal_reviewer_has_approve_permissions(self, legal_reviewer_user):
        """Legal reviewer should have approve and escalate permissions."""
        assert "contracts:read" in legal_reviewer_user.permissions
        assert "contracts:approve" in legal_reviewer_user.permissions
        assert "workflows:escalate" in legal_reviewer_user.permissions
        assert "audit:read" in legal_reviewer_user.permissions
        assert "reviews:export" in legal_reviewer_user.permissions
        assert "contracts:delete" not in legal_reviewer_user.permissions

    def test_auditor_has_audit_permissions(self, auditor_user):
        """Auditor should have audit read/export but no write permissions."""
        assert "audit:read" in auditor_user.permissions
        assert "audit:export" in auditor_user.permissions
        assert "reviews:export" in auditor_user.permissions
        assert "contracts:write" not in auditor_user.permissions
        assert "workflows:write" not in auditor_user.permissions

    def test_unknown_role_falls_back_to_viewer(self):
        """Unknown roles should fall back to viewer permissions."""
        user = UserContext(
            id="auth0|unknown",
            email="unknown@test.com",
            tenant_id="test-tenant-a",
            role="nonexistent_role",
            permissions=[],
        )
        resolved = resolve_permissions(user)
        assert "contracts:read" in resolved
        assert "contracts:write" not in resolved
        assert "workflows:write" not in resolved


class TestCanPolicy:
    """Policy-based authorization checks."""

    def test_admin_can_approve_review(self, rbac_admin_user):
        """Admin should be able to approve reviews."""
        assert can(rbac_admin_user, Actions.REVIEW_APPROVE)

    def test_viewer_cannot_approve_review(self, viewer_user):
        """Viewer should NOT be able to approve reviews."""
        assert not can(viewer_user, Actions.REVIEW_APPROVE)

    def test_legal_reviewer_can_approve_review(self, legal_reviewer_user):
        """Legal reviewer should be able to approve reviews."""
        assert can(legal_reviewer_user, Actions.REVIEW_APPROVE)

    def test_auditor_can_export(self, auditor_user):
        """Auditor should be able to export audit data."""
        assert can(auditor_user, Actions.AUDIT_EXPORT)

    def test_viewer_cannot_export_audit(self, viewer_user):
        """Viewer should NOT be able to export audit data."""
        assert not can(viewer_user, Actions.AUDIT_EXPORT)

    def test_admin_can_delete(self, rbac_admin_user):
        """Admin should be able to delete reviews."""
        assert can(rbac_admin_user, Actions.REVIEW_DELETE)

    def test_viewer_cannot_delete(self, viewer_user):
        """Viewer should NOT be able to delete reviews."""
        assert not can(viewer_user, Actions.REVIEW_DELETE)


class TestTenantIsolationInRBAC:
    """Tenant isolation in policy checks."""

    def test_can_denies_cross_tenant_access(self, tenant_admin_user, other_tenant_user):
        """Users should not be able to act on resources from other tenants."""
        # Simulate a resource from tenant_b
        resource = type("Resource", (), {"tenant_id": TENANT_B_ID_STR})()

        # Tenant A user should not be able to act on Tenant B resource
        assert not can(tenant_admin_user, Actions.REVIEW_READ, resource)

    def test_can_allows_same_tenant_access(self, rbac_admin_user):
        """Users should be able to act on resources from their own tenant."""
        resource = type("Resource", (), {"tenant_id": TENANT_A_ID_STR})()
        assert can(rbac_admin_user, Actions.REVIEW_READ, resource)

    def test_cross_tenant_export_blocked(self, auditor_user):
        """Auditor should not be able to export cross-tenant data."""
        resource = type("Resource", (), {"tenant_id": TENANT_B_ID_STR})()
        assert not can(auditor_user, Actions.AUDIT_EXPORT, resource)


class TestOwnershipChecks:
    """Ownership-based authorization for destructive actions."""

    def test_admin_can_delete_any_review(self, rbac_admin_user):
        """Admin should be able to delete any review in their tenant."""
        resource = type("Resource", (), {
            "tenant_id": TENANT_A_ID_STR,
            "created_by": "other-user",
            "assigned_to": None,
        })()
        assert can(rbac_admin_user, Actions.REVIEW_DELETE, resource)

    def test_reviewer_cannot_delete_others_review(self):
        """Regular reviewer should not delete reviews they don't own."""
        user = UserContext(
            id="auth0|reviewer",
            email="reviewer@test.com",
            tenant_id="test-tenant-a",
            role=Roles.REVIEWER,
            permissions=Roles.get_permissions(Roles.REVIEWER),
        )
        resource = type("Resource", (), {
            "tenant_id": "test-tenant-a",
            "created_by": "other-user",
            "assigned_to": None,
        })()
        assert not can(user, Actions.REVIEW_DELETE, resource)

    def test_reviewer_cannot_delete_own_review(self):
        """Reviewer should NOT be able to delete reviews (requires admin/legal_reviewer role)."""
        user = UserContext(
            id="auth0|reviewer",
            email="reviewer@test.com",
            tenant_id="test-tenant-a",
            role=Roles.REVIEWER,
            permissions=Roles.get_permissions(Roles.REVIEWER),
        )
        resource = type("Resource", (), {
            "tenant_id": "test-tenant-a",
            "created_by": "auth0|reviewer",
            "assigned_to": None,
        })()
        assert not can(user, Actions.REVIEW_DELETE, resource)
