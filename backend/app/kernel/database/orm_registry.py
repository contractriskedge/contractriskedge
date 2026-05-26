"""Register all SQLAlchemy ORM models on shared metadata.

Celery workers do not load FastAPI routers, so FK target tables (e.g. tenants)
must be imported explicitly before any session flush.
"""

from __future__ import annotations

import importlib

# Keep in sync with alembic/env.py domain imports.
_MODEL_MODULES = (
    "app.domains.tenants.models",
    "app.domains.ingestion.models",
    "app.domains.extraction.models",
    "app.domains.vectors.models",
    "app.domains.search.models",
    "app.domains.ai.models",
    "app.domains.review.models",
    "app.domains.notify.models",
    "app.domains.playbook.models",
    "app.domains.admin.models",
)


def register_orm_models() -> None:
    """Import all ORM modules so Base.metadata knows every referenced table."""
    for module in _MODEL_MODULES:
        importlib.import_module(module)
