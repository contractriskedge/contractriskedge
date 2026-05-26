from .integrations import router as integrations_router
from .oauth import router as oauth_router
from .webhooks import router as webhooks_router
from .sync import router as sync_router
from .credentials import router as credentials_router
from .permissions import router as permissions_router
from .audit import router as audit_router
from .governance import router as governance_router

__all__ = [
    "integrations_router",
    "oauth_router",
    "webhooks_router",
    "sync_router",
    "credentials_router",
    "permissions_router",
    "audit_router",
    "governance_router",
]
