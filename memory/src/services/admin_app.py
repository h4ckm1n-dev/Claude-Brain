"""Admin Service — administration, audit, sessions, documents, temporal.

Port 8108. Bundles 5 routers into a single admin service.
"""

from .base import create_app
from ..routers.admin import router as admin_router
from ..routers.audit import router as audit_router
from ..routers.sessions import router as sessions_router
from ..routers.documents import router as documents_router
from ..routers.temporal import router as temporal_router

app = create_app(
    title="Admin Service",
    routers=[admin_router, audit_router, sessions_router, documents_router, temporal_router],
    init_qdrant=True,
    init_docs=True,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.services.admin_app:app",
        host="0.0.0.0",
        port=8108,
        reload=False,
        log_level="info",
    )
