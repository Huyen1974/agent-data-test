from fastapi import FastAPI
from settings import settings

app = FastAPI()


@app.get("/healthz", tags=["Health"])
def health_check():
    """Confirms the API is running."""
    return {"status": "ok", "app_name": settings.APP_NAME}


@app.get("/readyz", tags=["Health"])
def readiness_check():
    """Confirms the API is ready to serve traffic."""
    # In a real app, this would check DB connections, etc.
    return {"status": "ready"}
