"""Search Service — semantic, keyword, and hybrid search.

Port 8103. Handles /memories/search, /search/unified, /query/enhance,
/context/*, and /memories/suggest endpoints.
"""

from .base import create_app
from ..routers.search import router as search_router

app = create_app(
    title="Search Service",
    routers=[search_router],
    init_qdrant=True,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.services.search_app:app",
        host="0.0.0.0",
        port=8103,
        reload=False,
        log_level="info",
    )
