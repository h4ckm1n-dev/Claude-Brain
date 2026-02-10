"""Analytics Service — memory statistics, trends, knowledge gaps.

Port 8107. Handles /analytics/* endpoints.
"""

from .base import create_app
from ..routers.analytics import router as analytics_router

app = create_app(
    title="Analytics Service",
    routers=[analytics_router],
    init_qdrant=True,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.services.analytics_app:app",
        host="0.0.0.0",
        port=8107,
        reload=False,
        log_level="info",
    )
