"""Compatibility re-export — integration models import Base from app.models.base.

This module bridges the integration subsystem (which uses app.models.base)
with the kernel's DeclarativeBase. All new models should import directly
from app.kernel.database.base instead.
"""

from app.kernel.database.base import Base

__all__ = ["Base"]
