"""FastAPI router registration.

Imports and registers all route modules with the main app.
"""

from fastapi import FastAPI


def register_routers(app: FastAPI) -> None:
    """Register all routers with the FastAPI application."""
    from .memories import router as memories_router
    from .search import router as search_router
    from .quality import router as quality_router
    from .brain import router as brain_router
    from .temporal import router as temporal_router
    from .analytics import router as analytics_router
    from .graph import router as graph_router
    from .documents import router as documents_router
    from .admin import router as admin_router
    from .audit import router as audit_router
    from .sessions import router as sessions_router

    app.include_router(memories_router)
    app.include_router(search_router)
    app.include_router(quality_router)
    app.include_router(brain_router)
    app.include_router(temporal_router)
    app.include_router(analytics_router)
    app.include_router(graph_router)
    app.include_router(documents_router)
    app.include_router(admin_router)
    app.include_router(audit_router)
    app.include_router(sessions_router)
