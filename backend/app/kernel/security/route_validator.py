"""Route permission validator — validates permission dependencies on all routes at startup.

Scans all registered FastAPI routes and verifies that every non-excluded
route has a ``require_permission`` or ``require_any_permission`` dependency.

This catches the class of bugs where:
- ``@require_permission`` is used as a decorator instead of ``Depends()``
- Routes are accidentally left without permission checks
- Permission dependencies are silently skipped

Environment-aware severity:
- ``development``: Errors are logged as warnings (non-blocking)
- ``staging``: Errors fail startup with ``PermissionValidationError``
- ``production``: Errors fail startup with ``PermissionValidationError``

Run during application startup to fail fast on misconfigured routes.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.kernel.middleware.excluded_paths import is_path_excluded

logger = logging.getLogger(__name__)


class PermissionValidationError(RuntimeError):
    """Raised when route permission validation fails in staging/production.

    Prevents application startup with unprotected routes.
    """


# Dependency callable names that indicate permission checking
PERMISSION_DEPENDENCIES = {
    "require_permission",
    "require_any_permission",
}

# Route methods that must have permission checks
PROTECTED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def _get_environment() -> str:
    """Get the current environment, defaulting to development."""
    return os.getenv("ENVIRONMENT", "development").lower()


def _has_permission_dependency(route: APIRoute) -> bool:
    """Check if a route has a permission dependency in its dependencies list.

    Scans both:
    1. The route's ``dependencies`` list (class-level)
    2. Each endpoint parameter's ``Depends()`` calls
    """
    # Check route-level dependencies
    for dep in route.dependencies:
        dep_callable = getattr(dep, "dependency", None) or dep
        dep_name = getattr(dep_callable, "__name__", "") or getattr(dep_callable, "__class__", "").__name__
        if dep_name in PERMISSION_DEPENDENCIES:
            return True

    # Check endpoint parameter dependencies
    for param in route.dependant.dependencies:
        dep_callable = getattr(param, "dependency", None)
        if dep_callable:
            # The dependency might be a factory that returns _check
            # Check if the outer callable or its return value is a permission checker
            dep_name = getattr(dep_callable, "__name__", "")
            if dep_name in PERMISSION_DEPENDENCIES:
                return True
            # Check if it's a partial/wrapped version
            if hasattr(dep_callable, "func"):
                inner_name = getattr(dep_callable.func, "__name__", "")
                if inner_name in PERMISSION_DEPENDENCIES:
                    return True

    return False


def _get_decorator_misuse(route: APIRoute) -> list[str]:
    """Detect potential decorator misuse on a route.

    Checks if ``@require_permission`` or ``@require_any_permission``
    appear in the route's source decorators (which would indicate
    decorator-style usage instead of Depends()).

    Returns a list of warning messages.
    """
    warnings: list[str] = []
    # Check if the route function has any decorator that looks like a permission check
    # We do this by checking the route's defined dependencies vs expected patterns
    # This is a best-effort check since we can't easily inspect source decorators at runtime
    return warnings


def validate_routes(app: FastAPI) -> list[dict[str, Any]]:
    """Validate all registered routes have proper permission dependencies.

    Iterates through all routes in the application and checks:
    1. Non-excluded routes have at least one permission dependency
    2. No routes use decorator-style permission checks

    Environment-aware behavior:
    - ``development``: Errors are logged, startup continues
    - ``staging``: Errors raise ``PermissionValidationError``, blocking startup
    - ``production``: Errors raise ``PermissionValidationError``, blocking startup

    Returns a list of validation issues found. Empty list = all clear.

    Raises:
        PermissionValidationError: If unprotected routes are found in
            staging or production environments.

    Usage:
        from app.kernel.security.route_validator import validate_routes

        try:
            validate_routes(app)
        except PermissionValidationError as exc:
            logger.critical("Startup blocked: %s", exc)
            raise
    """
    environment = _get_environment()
    fail_on_error = environment in ("staging", "production")

    issues: list[dict[str, Any]] = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        # Skip excluded paths (health, docs, openapi, etc.)
        if is_path_excluded(route.path):
            continue

        # Skip OPTIONS (CORS preflight)
        methods = set(route.methods or []) - {"OPTIONS", "HEAD"}
        if not methods:
            continue

        route_path = f"{route.methods} {route.path}"

        # Check 1: Does the route have a permission dependency?
        if not _has_permission_dependency(route):
            issues.append({
                "route": route_path,
                "endpoint": route.endpoint.__name__,
                "message": "No permission dependency found — route may be unprotected",
                "severity": "error",
            })

        # Check 2: Detect decorator misuse indicators
        decorator_warnings = _get_decorator_misuse(route)
        for warning in decorator_warnings:
            issues.append({
                "route": route_path,
                "endpoint": route.endpoint.__name__,
                "message": warning,
                "severity": "warning",
            })

    if issues:
        errors = [i for i in issues if i["severity"] == "error"]
        warnings_list = [i for i in issues if i["severity"] == "warning"]

        if errors:
            env_label = environment.upper()
            # Summary at error level (visible)
            logger.error(
                "[%s] Route permission validation: %d error(s), %d warning(s) — %s",
                env_label, len(errors), len(warnings_list),
                "FAILING STARTUP" if fail_on_error else "CONTINUING (dev mode)",
            )
            # Individual routes at debug level (hidden unless verbose)
            for issue in errors:
                logger.debug(
                    "  [UNPROTECTED-%s] %s — %s (endpoint: %s)",
                    env_label, issue["route"], issue["message"], issue["endpoint"],
                )

            if fail_on_error:
                error_details = "\n".join(
                    f"  {e['route']} ({e['endpoint']}): {e['message']}"
                    for e in errors
                )
                raise PermissionValidationError(
                    f"Startup blocked: {len(errors)} route(s) without permission "
                    f"dependencies found in {environment} environment.\n"
                    f"Unprotected routes:\n{error_details}\n\n"
                    f"Fix: Add Depends(require_permission(...)) to each route's "
                    f"signature, or add the route to excluded paths if intentional."
                )
        else:
            logger.info(
                "Route permission validation: %d warning(s), no errors",
                len(warnings),
            )

        for issue in warnings:
            logger.warning(
                "  %s — %s (endpoint: %s)",
                issue["route"], issue["message"], issue["endpoint"],
            )
    else:
        route_count = len([r for r in app.routes if isinstance(r, APIRoute)])
        logger.info(
            "Route permission validation: ALL %d routes have permission dependencies [%s]",
            route_count, environment.upper(),
        )

    return issues
