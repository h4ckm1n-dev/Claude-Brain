"""Graph Service — Neo4j knowledge graph operations.

Port 8104. Handles /graph/* endpoints. Does NOT require Qdrant.
"""

from .base import create_app
from ..routers.graph import router as graph_router

app = create_app(
    title="Graph Service",
    routers=[graph_router],
    init_qdrant=False,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.services.graph_app:app",
        host="0.0.0.0",
        port=8104,
        reload=False,
        log_level="info",
    )
