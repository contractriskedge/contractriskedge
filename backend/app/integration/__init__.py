"""
ContractRiskEdge / ContractEdge V1
Enterprise Integration + Connector Framework

Production-grade integration subsystem handling:
- Connector lifecycle management
- OAuth2 credential handling
- External sync orchestration
- Webhook ingestion & verification
- Rate-limit & retry-safe pipelines
- Integration governance & audit
- Structured observability & telemetry
"""

__version__ = "1.0.0"
__author__ = "ContractRiskEdge Engineering"

from . import models
from . import schemas
from . import services
from . import connectors
from . import routers
from . import workers

__all__ = [
    "models",
    "schemas",
    "services",
    "connectors",
    "routers",
    "workers",
]
