"""AI endpoint rate limit patterns — regex-based matching for paths with UUID segments.

The existing RateLimitMiddleware uses startswith matching, which fails for
paths like /api/v1/reviews/{uuid}/analyze. This module provides regex patterns
that correctly match AI endpoints regardless of UUID segments.

Each pattern defines:
- regex: compiled pattern matching the endpoint path
- per_user_limit: max requests per user within the user window
- per_tenant_limit: max requests per tenant within the tenant window
"""

from __future__ import annotations

import re
from typing import Final

from app.config import settings

# ── Pattern Tuple ─────────────────────────────────────────────────

AILimitPattern = tuple[re.Pattern[str], int, int]
"""Tuple of (compiled regex, per_user_limit, per_tenant_limit)."""


# ── AI Endpoint Patterns ──────────────────────────────────────────

AI_ENDPOINT_PATTERNS: Final[list[AILimitPattern]] = [
    (
        re.compile(r"^/api/v1/ai/analyze$"),
        settings.ai_rate_limit_analyze_per_user,
        settings.ai_rate_limit_analyze_per_tenant,
    ),
    (
        re.compile(r"^/api/v1/ai/copilot/suggest$"),
        settings.ai_rate_limit_copilot_per_user,
        settings.ai_rate_limit_copilot_per_tenant,
    ),
    (
        re.compile(r"^/api/v1/reviews/[^/]+/analyze$"),
        settings.ai_rate_limit_analyze_per_user,
        settings.ai_rate_limit_analyze_per_tenant,
    ),
    (
        re.compile(r"^/api/v1/reviews/[^/]+/re-analyze$"),
        3,  # re-analyze is less frequent
        settings.ai_rate_limit_analyze_per_tenant,
    ),
]


def match_ai_endpoint(path: str) -> AILimitPattern | None:
    """Check if a path matches an AI endpoint pattern.

    Args:
        path: The request URL path (e.g., /api/v1/ai/analyze).

    Returns:
        The matching (regex, user_limit, tenant_limit) tuple, or None.
    """
    for pattern, user_limit, tenant_limit in AI_ENDPOINT_PATTERNS:
        if pattern.match(path):
            return (pattern, user_limit, tenant_limit)
    return None
