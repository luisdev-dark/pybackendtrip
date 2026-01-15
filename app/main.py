from fastapi import FastAPI
from app.api.routes import health, routes, trips

app = FastAPI(
    title="RealGo MVP",
    version="0.1.0",
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(routes.router, prefix="/routes", tags=["routes"])
app.include_router(trips.router, prefix="/trips", tags=["trips"])
