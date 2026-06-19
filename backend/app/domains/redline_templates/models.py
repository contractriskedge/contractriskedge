"""RedlineTemplate — table already exists from migration. No ORM model needed.

The `redline_templates` table is created by Alembic migration
``34fb461caf36_add_redline_templates_table.py``. The repository uses
raw SQL via ``sqlalchemy.text()`` for all operations.

This file exists so the ``register_orm_models()`` scan can import it
without error. The table is already registered in the shared ``Base``
metadata by the migration.
"""

from __future__ import annotations

from app.kernel.database.base import Base
from app.domains.redline_templates._table import redline_templates_table

# Ensure the table is accessible via Base.metadata
if "redline_templates" not in Base.metadata.tables:
    Base.metadata.register(redline_templates_table)
