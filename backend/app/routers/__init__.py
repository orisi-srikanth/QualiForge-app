__all__ = ["api_router", "knowledge_router"]

def __getattr__(name: str):
    if name == "api_router":
        from backend.app.routers.api_router import router as api_router
        return api_router
    if name == "knowledge_router":
        from backend.app.routers.knowledge_router import router as knowledge_router
        return knowledge_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
