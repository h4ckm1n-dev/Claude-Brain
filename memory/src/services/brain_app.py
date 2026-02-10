"""Brain Service — replay, dream, importance scoring, inference.

Port 8105. Handles /brain/* endpoints.
"""

from .base import create_app
from ..routers.brain import router as brain_router

app = create_app(
    title="Brain Service",
    routers=[brain_router],
    init_qdrant=True,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.services.brain_app:app",
        host="0.0.0.0",
        port=8105,
        reload=False,
        log_level="info",
    )
