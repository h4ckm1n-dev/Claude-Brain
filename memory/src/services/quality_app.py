"""Quality Service — quality scoring, lifecycle, forgetting curves.

Port 8106. Handles /quality/* endpoints.
"""

from .base import create_app
from ..routers.quality import router as quality_router

app = create_app(
    title="Quality Service",
    routers=[quality_router],
    init_qdrant=True,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.services.quality_app:app",
        host="0.0.0.0",
        port=8106,
        reload=False,
        log_level="info",
    )
