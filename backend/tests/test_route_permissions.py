"""Route permission validation tests — ensures all routes have proper permission dependencies.

These tests verify that every registered API route (except explicitly excluded paths)
has a ``require_permission`` or ``require_any_permission`` dependency.

This prevents the class of bugs where:
- ``@require_permission`` is used as a decorator instead of ``Depends()``
- Routes are accidentally added without permission checks
- Permission regressions are introduced during refactoring

Run in CI to catch permission issues before merge:
    pytest tests/test_route_permissions.py -v
"""

from __future__ import annotations

from app.kernel.security.route_validator import validate_routes
from app.main import app


def test_all_routes_have_permission_dependencies():
    """Verify that every registered route has a permission dependency.

    This test imports the FastAPI app and runs the route validator
    against it. Any route missing a permission dependency will cause
    this test to fail.

    This is the CI enforcement counterpart to the startup validation
    in ``app/main.py``. While the startup validator blocks deployment
    in staging/production, this test catches issues during development
    before they reach CI.
    """
    issues = validate_routes(app)

    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]

    # Build a detailed failure message
    if errors:
        error_details = "\n".join(
            f"  ❌ {e['route']} ({e['endpoint']}): {e['message']}"
            for e in errors
        )
        warning_details = ""
        if warnings:
            warning_details = "\n".join(
                f"  ⚠️ {w['route']} ({w['endpoint']}): {w['message']}"
                for w in warnings
            )

        msg = (
            f"Found {len(errors)} route(s) without permission dependencies.\n"
            f"\nUnprotected routes:\n{error_details}\n"
            f"\nFix: Add ``Depends(require_permission(...))`` to each route's "
            f"signature, or add the route to excluded paths if intentional."
        )
        if warning_details:
            msg += f"\n\nWarnings:\n{warning_details}"

        raise AssertionError(msg)

    # Log warnings but don't fail the test
    if warnings:
        import logging
        logger = logging.getLogger(__name__)
        for w in warnings:
            logger.warning(
                "Route permission warning: %s — %s (endpoint: %s)",
                w["route"], w["message"], w["endpoint"],
            )


def test_specific_routes_have_permission_dependencies():
    """Verify that known high-risk routes have permission dependencies.

    This test checks specific routes that are commonly targeted for
    permission bypass or are frequently modified:
    - All review CRUD routes
    - All workflow action routes (assign, escalate, approve)
    - All admin routes
    - All benchmark routes
    - All search routes
    """
    from fastapi.routing import APIRoute

    # Routes that MUST have permission dependencies
    critical_patterns = [
        "/api/v1/reviews",
        "/api/v1/workflows",
        "/api/v1/admin",
        "/api/v1/benchmarks",
        "/api/v1/search",
        "/api/v1/playbook",
        "/api/v1/notifications",
    ]

    unprotected: list[str] = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        # Check if this route matches a critical pattern
        if not any(route.path.startswith(p) for p in critical_patterns):
            continue

        # Skip OPTIONS (CORS preflight)
        methods = set(route.methods or []) - {"OPTIONS", "HEAD"}
        if not methods:
            continue

        # Check for permission dependency
        from app.kernel.security.route_validator import _has_permission_dependency
        if not _has_permission_dependency(route):
            unprotected.append(f"{route.methods} {route.path} ({route.endpoint.__name__})")

    if unprotected:
        raise AssertionError(
            f"Found {len(unprotected)} critical route(s) without permission dependencies:\n"
            + "\n".join(f"  ❌ {r}" for r in unprotected)
        )

